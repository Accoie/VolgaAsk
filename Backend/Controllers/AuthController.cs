using Microsoft.AspNetCore.Authentication;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Identity;
using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.RateLimiting;
using Microsoft.EntityFrameworkCore;

namespace VolgaAsk;

[ApiController, Route("api/auth")]
public sealed class AuthController(AppDb db, PasswordHasher<Account> hasher, CredentialRules rules) : ControllerBase
{
    [AllowAnonymous, EnableRateLimiting("login"), HttpPost("login")]
    public async Task<ActionResult<AccountInfo>> Login(Credentials input, CancellationToken ct)
    {
        var account = await db.Accounts.SingleOrDefaultAsync(x => x.Login == input.Login, ct);
        if (input.Password.Length > 128 || account is null || !account.Authenticate(input.Password, hasher))
            return Unauthorized();
        await db.SaveChangesAsync(ct);
        return await SignInAccount(account);
    }

    [AllowAnonymous, EnableRateLimiting("login"), HttpPost("register")]
    public async Task<ActionResult<AccountInfo>> Register(Registration input, CancellationToken ct)
    {
        var validation = rules.Validate(input);
        if (!validation.IsValid)
            return BadRequest(string.Join(" ", validation.Errors.Select(x => x.ErrorMessage)));

        var account = Account.Create(input.Login, input.Name, input.Password, Role.User, hasher);
        if (!await db.TryCreate(account, ct))
            return Conflict("Этот логин уже занят.");
        return StatusCode(201, await SignInAccount(account));
    }

    private async Task<AccountInfo> SignInAccount(Account account)
    {
        await HttpContext.SignInAsync(account.Principal());
        return new AccountInfo(account.Id, account.Login, account.Name, account.Role);
    }

    [HttpGet("me")]
    public async Task<ActionResult<AccountInfo>> Me(CancellationToken ct)
    {
        var account = await db.Accounts.FindAsync([User.AccountId()], ct);
        if (account is null)
            return Unauthorized();
        return new AccountInfo(account.Id, account.Login, account.Name, account.Role);
    }

    [HttpPost("logout")]
    public async Task<IActionResult> Logout()
    {
        await HttpContext.SignOutAsync();
        return NoContent();
    }
}
