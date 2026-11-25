using System.Net.Http.Json;
using System.Text.Json;

namespace VolgaAsk;

public record GeneratedFile(string Title, byte[] Content, string Preview);
public record DocumentStep(string Answer, JsonElement Session, string State, GeneratedFile? File);
public record ReviewReport(string Report);
public record ReviewFailure(string Detail);
public sealed class ReviewException(string message) : Exception(message);
public record ReviewPermission(bool AllowExternal);

public sealed class Documents(IHttpClientFactory clients)
{
    public async Task<DocumentStep?> Advance(string question, string? draft, string mode, string? lastDocument, CancellationToken ct)
    {
        var session = draft == null ? (JsonElement?)null : JsonSerializer.Deserialize<JsonElement>(draft);
        using var client = clients.CreateClient("generator");
        var previous = lastDocument == null ? (JsonElement?)null : JsonSerializer.Deserialize<JsonElement>(lastDocument);
        using var response = await client.PostAsJsonAsync("message", new { question, session, previous, mode }, ct);
        response.EnsureSuccessStatusCode();
        return await response.Content.ReadFromJsonAsync<DocumentStep>(ct);
    }

    public async Task<string> Review(Guid chatId, Guid fileId, bool external, CancellationToken ct)
    {
        using var client = clients.CreateClient("reviewer");
        using var response = await client.PostAsJsonAsync($"review/{chatId}/{fileId}", new { allow_external = external }, ct);
        if (response.StatusCode == System.Net.HttpStatusCode.UnprocessableEntity)
        {
            var failure = await response.Content.ReadFromJsonAsync<ReviewFailure>(ct);
            throw new ReviewException(failure?.Detail ?? "Проверка прервана.");
        }
        response.EnsureSuccessStatusCode();
        return (await response.Content.ReadFromJsonAsync<ReviewReport>(ct))!.Report;
    }

    public static string Folder(Guid chatId) => Path.Combine("/storage", chatId.ToString());
    public static string PathFor(Guid chatId, Guid fileId) => Path.Combine(Folder(chatId), $"{fileId}.docx");

    public static async Task Save(Guid chatId, Guid fileId, byte[] data, CancellationToken ct)
    {
        Directory.CreateDirectory(Folder(chatId));
        await File.WriteAllBytesAsync(PathFor(chatId, fileId), data, ct);
    }
}
