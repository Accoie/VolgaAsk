using System.ComponentModel.DataAnnotations;
using System.Security.Claims;
using FluentValidation;

namespace VolgaAsk;

public record Credentials(string Login, string Password);
public record Registration(string Login, string Name, string Password);
public record CreateAccount(string Login, string Name, string Password, [Required] Role? Role);
public record ChangeRole([Required] Role? Role);
public record AccountInfo(Guid Id, string Login, string Name, Role Role);
public sealed class CredentialRules : AbstractValidator<Registration>
{
    public CredentialRules()
    {
        RuleFor(x => x.Login).NotEmpty().Matches("^[a-zA-Z0-9_.-]{3,64}\\z")
            .WithMessage("Логин должен содержать от 3 до 64 латинских букв, цифр или символов . _ -");
        RuleFor(x => x.Name).NotEmpty().MaximumLength(80)
            .WithMessage("Введите имя длиной до 80 символов.");
        RuleFor(x => x.Password).NotEmpty().Length(10, 128)
            .WithMessage("Длина пароля должна быть от 10 до 128 символов.");
    }
}

public static class Claims
{
    public static Guid AccountId(this ClaimsPrincipal user) =>
        Guid.Parse(user.FindFirstValue(ClaimTypes.NameIdentifier)!);
}
