using System.Security.Claims;
using Microsoft.AspNetCore.Identity;

namespace VolgaAsk;

public enum Role { User, Employee, Admin }

public sealed class Account
{
    public Guid Id { get; private set; } = Guid.NewGuid();
    public string Login { get; private set; } = "";
    public string Name { get; private set; } = "";
    public string PasswordHash { get; private set; } = "";
    public Role Role { get; private set; }

    public static Account Create(string login, string name, string password, Role role, PasswordHasher<Account> hasher)
    {
        var account = new Account { Login = login, Name = name.Trim(), Role = role };
        account.PasswordHash = hasher.HashPassword(account, password);
        return account;
    }

    public bool Authenticate(string password, PasswordHasher<Account> hasher)
    {
        var result = hasher.VerifyHashedPassword(this, PasswordHash, password);
        if (result == PasswordVerificationResult.SuccessRehashNeeded)
            PasswordHash = hasher.HashPassword(this, password);
        return result != PasswordVerificationResult.Failed;
    }

    public bool ChangeRole(Guid actor, Role role)
    {
        if (Id == actor && role != Role.Admin)
            return false;
        Role = role;
        return true;
    }

    public ClaimsPrincipal Principal() => new(new ClaimsIdentity(new[]
    {
        new Claim(ClaimTypes.NameIdentifier, Id.ToString()),
        new Claim(ClaimTypes.Name, Login),
        new Claim(ClaimTypes.Role, Role.ToString())
    }, "Cookies"));
}
