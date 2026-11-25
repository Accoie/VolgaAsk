using System.Text;
using System.Text.Json;
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;

namespace VolgaAsk;

[ApiController, Route("api/chats")]
public sealed class ChatsController(AppDb db, RagClient rag, ILogger<ChatsController> logger) : ControllerBase
{
    private IQueryable<Chat> Owned => db.Chats.Where(x => x.OwnerId == User.AccountId());

    [HttpGet]
    public Task<List<ChatInfo>> List(CancellationToken ct) => Owned.OrderByDescending(x => x.UpdatedAt)
        .Select(x => new ChatInfo(x.Id, x.Title, x.UpdatedAt)).ToListAsync(ct);

    [HttpPost]
    public async Task<ActionResult<ChatInfo>> Create(CancellationToken ct)
    {
        var chat = Chat.Start(User.AccountId());
        db.Chats.Add(chat);
        await db.SaveChangesAsync(ct);
        return CreatedAtAction(nameof(History), new { id = chat.Id }, new ChatInfo(chat.Id, chat.Title, chat.UpdatedAt));
    }

    [HttpGet("{id:guid}/messages")]
    public async Task<ActionResult<List<Turn>>> History(Guid id, CancellationToken ct)
    {
        if (!await Owned.AnyAsync(x => x.Id == id, ct))
            return NotFound();
        return await db.Turns.Where(x => x.ChatId == id).OrderBy(x => x.Id).ToListAsync(ct);
    }

    [HttpPost("{id:guid}/messages"), Produces("text/event-stream")]
    [ProducesResponseType(typeof(string), 200)]
    public async Task<IActionResult> Send(Guid id, Ask input, CancellationToken ct)
    {
        await using var transaction = await db.Database.BeginTransactionAsync(ct);
        if (!await TryLockChat(id, ct))
            return Conflict();
        var chat = await Owned.SingleOrDefaultAsync(x => x.Id == id, ct);
        if (chat is null)
            return NotFound();

        await db.Entry(chat).Collection(x => x.Turns).Query().OrderByDescending(x => x.Id).Take(4).LoadAsync(ct);
        var question = input.Question.Trim();
        Response.ContentType = "text/event-stream; charset=utf-8";
        Response.Headers.CacheControl = "no-cache";
        using var timeout = CancellationTokenSource.CreateLinkedTokenSource(ct);
        timeout.CancelAfter(TimeSpan.FromMinutes(10));
        try
        {
            var answer = await StreamAnswer(question, chat, timeout.Token);
            chat.Complete(question, answer);
            await db.SaveChangesAsync(ct);
            await transaction.CommitAsync(ct);
            await Emit("done", "", ct);
        }
        catch (Exception ex) when (!ct.IsCancellationRequested)
        {
            logger.LogWarning(ex, "Ошибка ответа в чате {Id}", id);
            await Emit("error", "Не удалось завершить ответ. Попробуйте ещё раз.", ct);
        }
        return new EmptyResult();
    }

    [HttpDelete("{id:guid}")]
    public async Task<IActionResult> Delete(Guid id, CancellationToken ct)
    {
        await using var transaction = await db.Database.BeginTransactionAsync(ct);
        var chat = Owned.Where(x => x.Id == id);
        if (!await chat.AnyAsync(ct))
            return NotFound();
        if (!await TryLockChat(id, ct))
            return Conflict("Дождитесь завершения ответа в этом чате.");
        var deleted = await chat.ExecuteDeleteAsync(ct);
        await transaction.CommitAsync(ct);
        return deleted == 0 ? NotFound() : NoContent();
    }

    private Task<bool> TryLockChat(Guid id, CancellationToken ct) =>
        db.Database.SqlQuery<bool>(
            $"SELECT pg_try_advisory_xact_lock(hashtextextended({id.ToString()}, 0)) AS \"Value\"").SingleAsync(ct);

    private async Task<string> StreamAnswer(string question, Chat chat, CancellationToken ct)
    {
        var answer = new StringBuilder();
        await foreach (var item in rag.Answer(question, chat.RecentHistory(), ct))
        {
            answer.Append(item.Text);
            await Emit("token", item.Text, ct);
        }
        if (answer.Length == 0)
            throw new InvalidDataException("RAG вернул пустой ответ.");
        return answer.ToString();
    }

    private async Task Emit(string type, string text, CancellationToken ct)
    {
        await Response.WriteAsync($"data: {JsonSerializer.Serialize(new { type, text }, EventJson)}\n\n", ct);
        await Response.Body.FlushAsync(ct);
    }

    private static readonly JsonSerializerOptions EventJson = new()
    {
        Encoder = System.Text.Encodings.Web.JavaScriptEncoder.UnsafeRelaxedJsonEscaping
    };
}
