namespace VolgaAsk;

public sealed class Chat
{
    public Guid Id { get; private set; } = Guid.NewGuid();
    public Guid OwnerId { get; private set; }
    public string Title { get; private set; } = "Новый чат";
    public DateTime UpdatedAt { get; private set; } = DateTime.UtcNow;
    public List<Turn> Turns { get; private set; } = new();
    public string? Draft { get; private set; }

    public static Chat Start(Guid owner) => new() { OwnerId = owner };

    public string RecentHistory()
    {
        var history = string.Join("\n", Turns.OrderBy(x => x.Id)
            .Select(x => $"Пользователь: {x.Question}\nАссистент: {x.Answer}"));
        return history.Length <= 12000 ? history : history[^12000..];
    }

    public Turn Complete(string question, string answer, DocumentStep? step = null, Guid? fileId = null)
    {
        if (Turns.Count == 0)
            Title = string.Concat(question.EnumerateRunes().Take(64));
        var turn = new Turn(Id, question, answer);
        if (step != null)
        {
            Draft = step.State is "GENERATED" or "CANCELLED" ? null : step.Session.GetRawText();
            turn.RecordStep(step, fileId);
        }
        Turns.Add(turn);
        UpdatedAt = DateTime.UtcNow;
        return turn;
    }
}

public sealed class Turn
{
    public long Id { get; private set; }
    public Guid ChatId { get; private set; }
    public string Question { get; private set; }
    public string Answer { get; private set; }
    public Guid? FileId { get; private set; }
    public string? DocumentTitle { get; private set; }
    public string? Preview { get; private set; }
    public string? Report { get; private set; }
    public bool AwaitingConfirmation { get; private set; }
    [System.Text.Json.Serialization.JsonIgnore]
    public string? Revision { get; private set; }

    public void RecordStep(DocumentStep step, Guid? fileId)
    {
        AwaitingConfirmation = step.State == "REVIEW";
        FileId = fileId;
        DocumentTitle = step.File?.Title;
        Preview = step.File?.Preview;
        if (fileId.HasValue) Revision = step.Session.GetRawText();
    }

    public void SetReport(string report) => Report = report;

    public Turn(Guid chatId, string question, string answer)
    {
        ChatId = chatId;
        Question = question;
        Answer = answer;
    }
}
