using System.Runtime.CompilerServices;
using System.Text.Json;

namespace VolgaAsk;

public sealed class RagClient(HttpClient http)
{
    private static readonly JsonSerializerOptions Json = new(JsonSerializerDefaults.Web);

    public async IAsyncEnumerable<RagEvent> Answer(string question, string history,
        [EnumeratorCancellation] CancellationToken ct)
    {
        using var request = new HttpRequestMessage(HttpMethod.Post, "chat")
        {
            Content = JsonContent.Create(new { question, history })
        };
        using var response = await http.SendAsync(request, HttpCompletionOption.ResponseHeadersRead, ct);
        response.EnsureSuccessStatusCode();
        using var reader = new StreamReader(await response.Content.ReadAsStreamAsync(ct));
        while (await reader.ReadLineAsync(ct) is { } line)
        {
            if (!line.StartsWith("data: ", StringComparison.Ordinal))
                continue;
            var item = JsonSerializer.Deserialize<RagEvent>(line.AsSpan(6), Json);
            if (item?.Type == "done")
                yield break;
            if (item?.Type != "token" || item.Text is null)
                throw new InvalidDataException("Ошибка потока RAG.");
            yield return item;
        }
        throw new EndOfStreamException("Оборвался поток RAG.");
    }
}
