using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Identity;
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;

namespace VolgaAsk;

[ApiController, Authorize(Roles = nameof(Role.Admin)), Route("api/accounts")]
public sealed class AccountsController(AppDb db, PasswordHasher<Account> hasher, CredentialRules rules) : ControllerBase
{
    [HttpGet]
    public Task<List<AccountInfo>> List(CancellationToken ct) => db.Accounts.OrderBy(x => x.Login)
        .Select(x => new AccountInfo(x.Id, x.Login, x.Name, x.Role)).ToListAsync(ct);

    [HttpPost]
    public async Task<ActionResult<AccountInfo>> Create(CreateAccount input, CancellationToken ct)
    {
        var validation = rules.Validate(new Registration(input.Login, input.Name, input.Password));
        if (!validation.IsValid)
            return BadRequest(string.Join(" ", validation.Errors.Select(x => x.ErrorMessage)));

        var account = Account.Create(input.Login, input.Name, input.Password, input.Role!.Value, hasher);
        if (!await db.TryCreate(account, ct))
            return Conflict("Этот логин уже занят.");
        return StatusCode(201, new AccountInfo(account.Id, account.Login, account.Name, account.Role));
    }

    [HttpPut("{id:guid}/role")]
    public async Task<IActionResult> SetRole(Guid id, ChangeRole input, CancellationToken ct)
    {
        var account = await db.Accounts.FindAsync([id], ct);
        if (account is null)
            return NotFound();
        if (!account.ChangeRole(User.AccountId(), input.Role!.Value))
            return Conflict("Нельзя снять роль администратора с себя.");
        await db.SaveChangesAsync(ct);
        return NoContent();
    }
}
