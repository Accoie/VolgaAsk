using System.Text;
using System.Text.Json;
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;

namespace VolgaAsk;

[ApiController, Route("api/chats")]
public sealed class ChatsController(AppDb db, RagClient rag, Documents documents, ILogger<ChatsController> logger) : ControllerBase
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
        var draft = chat.Draft;
        var mode = input.Mode;
        if (input.ReviseFile.HasValue)
        {
            draft = await db.Turns.Where(t => t.ChatId == id && t.FileId == input.ReviseFile)
                .Select(t => t.Revision).SingleOrDefaultAsync(ct);
            if (draft == null) return NotFound();
            mode = "revise";
        }
        Response.ContentType = "text/event-stream; charset=utf-8";
        Response.Headers.CacheControl = "no-cache";
        using var timeout = CancellationTokenSource.CreateLinkedTokenSource(ct);
        timeout.CancelAfter(TimeSpan.FromMinutes(10));
        Guid? fileId = null;
        var committed = false;
        try
        {
            var previous = draft == null && mode == "auto"
                ? await db.Turns.Where(t => t.ChatId == id && t.FileId != null).OrderByDescending(t => t.Id)
                    .Select(t => t.Revision).FirstOrDefaultAsync(ct) : null;
            var step = mode == "question" ? null : await documents.Advance(question, draft, mode, previous, timeout.Token);
            var answer = step?.Answer ?? await StreamAnswer(question, chat, timeout.Token);
            if (step?.State == "REVIEW")
                answer += "\n\nПосле подтверждения обезличенная копия пройдёт проверку в GigaChat.";
            if (step?.File is { } file)
            {
                fileId = Guid.NewGuid();
                await Documents.Save(id, fileId.Value, file.Content, ct);
            }
            var turn = chat.Complete(question, answer, step, fileId);
            await db.SaveChangesAsync(ct);
            await transaction.CommitAsync(ct);
            committed = true;
            if (fileId.HasValue)
                await ReviewGenerated(turn);
            else if (step != null)
                await Emit("token", answer, ct);
            await Emit("done", "", ct);
        }
        catch (Exception ex) when (!ct.IsCancellationRequested)
        {
            logger.LogWarning(ex, "Ошибка ответа в чате {Id}", id);
            await Emit("error", "Не удалось завершить ответ. Попробуйте ещё раз.", ct);
        }
        finally
        {
            if (!committed && fileId.HasValue) System.IO.File.Delete(Documents.PathFor(id, fileId.Value));
        }
        return new EmptyResult();
    }

    private async Task ReviewGenerated(Turn turn)
    {
        try
        {
            await Emit("status", "Документ сформирован. Обезличиваю и проверяю его…", HttpContext.RequestAborted);
        }
        catch (Exception) when (HttpContext.RequestAborted.IsCancellationRequested) { }
        try
        {
            turn.SetReport(await documents.Review(turn.ChatId, turn.FileId!.Value, true, CancellationToken.None));
        }
        catch (ReviewException ex)
        {
            turn.SetReport(ex.Message);
        }
        catch (Exception ex) when (ex is HttpRequestException or OperationCanceledException)
        {
            turn.SetReport("Проверка не завершена. Документ сохранён и доступен для скачивания.");
        }
        await db.SaveChangesAsync();
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
        if (deleted > 0 && Directory.Exists(Documents.Folder(id)))
            Directory.Delete(Documents.Folder(id), true);
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
