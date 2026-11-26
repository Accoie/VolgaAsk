using System.ComponentModel.DataAnnotations;
using System.Text.Json;
using System.Text.Json.Serialization;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;

namespace VolgaAsk;

public sealed record TemplateComponent([Required, MaxLength(160)] string Label, bool Required = true,
    [MaxLength(500)] string? Question = null);
public sealed record ParagraphEdit(int Paragraph, int Start, int End, string? Component, string Text = "");
public sealed record TemplateFieldSettings(string Key, string Label, bool Required, string? Question);
public sealed record TemplateChanges([Required, MaxLength(500)] string Title, int Revision,
    [Required, MaxLength(2000)] List<ParagraphEdit> Edits,
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] List<TemplateFieldSettings>? Fields = null);

[ApiController, Route("api/templates"), Authorize(Roles = "Admin,Employee")]
public sealed class TemplatesController(IHttpClientFactory clients) : ControllerBase
{
    [HttpGet]
    public Task<IActionResult> Library(CancellationToken ct) => Forward("templates", ct);

    [HttpGet("catalog")]
    public Task<IActionResult> Catalog(CancellationToken ct) => Forward("templates/catalog", ct);

    [HttpPost("catalog/{source:regex(^[[0-9a-f]]+$)}/import")]
    public Task<IActionResult> Import(string source, CancellationToken ct) =>
        Forward($"templates/catalog/{source}/import", ct, HttpMethod.Post);

    [HttpPost("components")]
    public Task<IActionResult> CreateComponent(TemplateComponent component, CancellationToken ct) =>
        Forward("templates/components", ct, HttpMethod.Post, component);

    [HttpGet("{id:regex(^[[a-z0-9_]]+$)}/editor")]
    public Task<IActionResult> Editor(string id, CancellationToken ct) => Forward($"templates/{id}/editor", ct);

    [HttpGet("{id:regex(^[[a-z0-9_]]+$)}/source")]
    public Task<IActionResult> Source(string id, CancellationToken ct) => Forward($"templates/{id}/source", ct);

    [HttpPost("{id:regex(^[[a-z0-9_]]+$)}/preview")]
    public Task<IActionResult> Preview(string id, TemplateChanges changes, CancellationToken ct) =>
        Forward($"templates/{id}/preview", ct, HttpMethod.Post, changes);

    [HttpPost("{id:regex(^[[a-z0-9_]]+$)}/publish")]
    public Task<IActionResult> Publish(string id, TemplateChanges changes, CancellationToken ct) =>
        Forward($"templates/{id}/publish", ct, HttpMethod.Post, changes);

    private async Task<IActionResult> Forward(string path, CancellationToken ct, HttpMethod? method = null,
        object? body = null)
    {
        using var client = clients.CreateClient("generator");
        using var request = new HttpRequestMessage(method ?? HttpMethod.Get, path);
        if (body is not null) request.Content = JsonContent.Create(body);
        using var response = await client.SendAsync(request, ct);
        if (!response.IsSuccessStatusCode)
        {
            var message = "Не удалось обработать запрос к каталогу шаблонов.";
            if (response.Content.Headers.ContentType?.MediaType == "application/json")
            {
                using var json = JsonDocument.Parse(await response.Content.ReadAsStreamAsync(ct));
                if (json.RootElement.TryGetProperty("detail", out var detail) && detail.ValueKind == JsonValueKind.String)
                    message = detail.GetString()!;
            }
            return new ContentResult { StatusCode = (int)response.StatusCode, ContentType = "text/plain; charset=utf-8",
                Content = message };
        }
        return File(await response.Content.ReadAsByteArrayAsync(ct),
            response.Content.Headers.ContentType?.MediaType ?? "application/json");
    }
}
