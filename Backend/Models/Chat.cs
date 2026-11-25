namespace VolgaAsk;

public sealed class Chat
{
    public Guid Id { get; private set; } = Guid.NewGuid();
    public Guid OwnerId { get; private set; }
    public string Title { get; private set; } = "Новый чат";
    public DateTime UpdatedAt { get; private set; } = DateTime.UtcNow;
    public List<Turn> Turns { get; private set; } = new();

    public static Chat Start(Guid owner) => new() { OwnerId = owner };

    public string RecentHistory()
    {
        var history = string.Join("\n", Turns.OrderBy(x => x.Id)
            .Select(x => $"Пользователь: {x.Question}\nАссистент: {x.Answer}"));
        return history.Length <= 12000 ? history : history[^12000..];
    }

    public void Complete(string question, string answer)
    {
        if (Turns.Count == 0)
            Title = string.Concat(question.EnumerateRunes().Take(64));
        Turns.Add(new Turn(Id, question, answer));
        UpdatedAt = DateTime.UtcNow;
    }
}

public sealed class Turn
{
    public long Id { get; private set; }
    public Guid ChatId { get; private set; }
    public string Question { get; private set; }
    public string Answer { get; private set; }
    public Turn(Guid chatId, string question, string answer)
    {
        ChatId = chatId;
        Question = question;
        Answer = answer;
    }
}
