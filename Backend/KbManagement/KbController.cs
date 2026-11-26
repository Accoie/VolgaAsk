using System.ComponentModel.DataAnnotations;
using System.Security.Cryptography;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using Npgsql;

namespace VolgaAsk;

public sealed record PortalImport([Required] string Url, [Required] string Checksum);

[ApiController, Route("api/kb"), Authorize(Roles = "Admin,Employee")]
public sealed class KbController(KbStore store, IConfiguration config) : ControllerBase
{
    private const int Limit = 48 * 1024 * 1024;

    [HttpGet("documents")]
    public Task<List<KbDocument>> Documents(CancellationToken ct) => store.Documents(ct);

    [HttpGet("catalog")]
    public async Task<IActionResult> Catalog(CancellationToken ct) =>
        Ok(new { documents = await store.Catalog(ct), sync = await store.Sync(ct) });

    [HttpPost("import")]
    public async Task<IActionResult> Import(PortalImport input, CancellationToken ct)
    {
        var id = Guid.NewGuid();
        return await store.Import(id, input.Url, input.Checksum, ct) == 1
            ? Accepted(new { id }) : Conflict("Документ уже добавлен или каталог изменился.");
    }

    [HttpPost("upload"), Consumes("multipart/form-data"), RequestSizeLimit(Limit + 65536)]
    public async Task<IActionResult> Upload(IFormFile file, [FromForm, MaxLength(500)] string title,
        [FromForm] DateOnly date, CancellationToken ct)
    {
        if (string.IsNullOrWhiteSpace(title) || date == default)
            return BadRequest("Укажите официальное название и дату документа.");
        if (file.Length < 5 || file.Length > Limit || !file.FileName.EndsWith(".pdf", StringComparison.OrdinalIgnoreCase))
            return BadRequest("Выберите PDF размером до 48 МБ.");
        using var stream = new MemoryStream((int)file.Length);
        await file.CopyToAsync(stream, ct);
        var pdf = stream.ToArray();
        if (!pdf.AsSpan().StartsWith("%PDF-"u8)) return BadRequest("Файл не является PDF.");
        var id = Guid.NewGuid();
        var hash = Convert.ToHexString(SHA256.HashData(pdf)).ToLowerInvariant();
        var filename = Path.GetFileName(file.FileName.Replace('\\', '/'));
        return await store.Upload(id, title.Trim(), filename, date, hash, pdf, ct) == 1
            ? Accepted(new { id }) : Conflict("Этот PDF уже есть в базе или ожидает индексации.");
    }

    [HttpGet("documents/{id:guid}/file")]
    public async Task<IActionResult> Open(Guid id, CancellationToken ct)
    {
        var ready = await store.Database.SqlQuery<bool>($"""
            SELECT EXISTS(SELECT 1 FROM kb_documents WHERE id={id} AND status='ready') AS "Value"
            """).SingleAsync(ct);
        var path = Path.Combine(config["KB_ROOT"] ?? "/storage/kb", "raw", $"{id}.pdf");
        if (!ready) return NotFound();
        Response.Headers["X-Content-Type-Options"] = "nosniff";
        Response.Headers.ContentSecurityPolicy = "sandbox";
        try
        {
            var stream = new FileStream(path, FileMode.Open, FileAccess.Read, FileShare.Read | FileShare.Delete);
            return File(stream, "application/pdf", enableRangeProcessing: true);
        }
        catch (FileNotFoundException) { return NotFound(); }
    }

    [HttpDelete("documents/{id:guid}")]
    public async Task<IActionResult> Delete(Guid id, CancellationToken ct) =>
        await store.Delete(id, ct) == 1 ? Accepted() : Conflict("Документ уже удалён или обрабатывается.");

    [HttpGet("changes")]
    public async Task<IActionResult> Changes(CancellationToken ct)
    {
        var connection = (NpgsqlConnection)store.Database.GetDbConnection();
        await connection.OpenAsync(ct);
        await using var command = new NpgsqlCommand("LISTEN kb_changes", connection);
        await command.ExecuteNonQueryAsync(ct);
        await connection.WaitAsync(15000, ct);
        return NoContent();
    }
}
