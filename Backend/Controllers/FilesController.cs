using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;

namespace VolgaAsk;

[ApiController, Route("api/chats/{chatId:guid}/files")]
public sealed class FilesController(AppDb db, Documents documents) : ControllerBase
{
    private IQueryable<Turn> Owned(Guid chatId, Guid fileId) => db.Turns.Where(t =>
        t.ChatId == chatId && t.FileId == fileId && db.Chats.Any(c => c.Id == chatId && c.OwnerId == User.AccountId()));

    [HttpGet("{fileId:guid}")]
    public async Task<IActionResult> Download(Guid chatId, Guid fileId, CancellationToken ct)
    {
        var turn = await Owned(chatId, fileId).SingleOrDefaultAsync(ct);
        var path = Documents.PathFor(chatId, fileId);
        if (turn == null || !System.IO.File.Exists(path)) return NotFound();
        return PhysicalFile(path, "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            turn.DocumentTitle + ".docx");
    }

    [HttpPost("{fileId:guid}/review")]
    public async Task<ActionResult<ReviewReport>> Review(Guid chatId, Guid fileId, ReviewPermission input, CancellationToken ct)
    {
        var turn = await Owned(chatId, fileId).SingleOrDefaultAsync(ct);
        if (turn == null) return NotFound();
        string report;
        try
        {
            report = await documents.Review(chatId, fileId, input.AllowExternal, ct);
        }
        catch (ReviewException error)
        {
            return UnprocessableEntity(error.Message);
        }
        turn.SetReport(report);
        await db.SaveChangesAsync(ct);
        return new ReviewReport(report);
    }
}
