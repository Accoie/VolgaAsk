using Microsoft.AspNetCore.Authentication.Cookies;
using Microsoft.AspNetCore.Identity;
using Microsoft.EntityFrameworkCore;

namespace VolgaAsk;

public static class Auth
{
    public static void Configure(CookieAuthenticationOptions options)
    {
        options.Cookie.Name = "volgaask.session";
        options.Cookie.HttpOnly = true;
        options.Cookie.SameSite = SameSiteMode.Strict;
        options.ExpireTimeSpan = TimeSpan.FromHours(8);
        options.Events.OnRedirectToLogin = context => Status(context.Response, 401);
        options.Events.OnRedirectToAccessDenied = context => Status(context.Response, 403);
        options.Events.OnValidatePrincipal = ValidateSession;
    }

    private static Task Status(HttpResponse response, int status)
    {
        response.StatusCode = status;
        return Task.CompletedTask;
    }

    private static async Task ValidateSession(CookieValidatePrincipalContext context)
    {
        var db = context.HttpContext.RequestServices.GetRequiredService<AppDb>();
        var account = await db.Accounts.FindAsync(context.Principal!.AccountId());
        if (account is null)
            context.RejectPrincipal();
        else if (!context.Principal!.IsInRole(account.Role.ToString()))
            context.ReplacePrincipal(account.Principal());
    }

    public static async Task Initialize(IServiceProvider services, IConfiguration config)
    {
        using var scope = services.CreateScope();
        var db = scope.ServiceProvider.GetRequiredService<AppDb>();
        await db.Database.EnsureCreatedAsync();
        await db.UpgradeAccounts();
        if (await db.Accounts.AnyAsync())
            return;

        var credentials = new Registration(config["ADMIN_LOGIN"] ?? "admin",
            config["ADMIN_NAME"] ?? "Администратор", config["ADMIN_PASSWORD"] ?? "");
        if (!new CredentialRules().Validate(credentials).IsValid)
            throw new InvalidOperationException("Проверьте ADMIN_LOGIN, ADMIN_NAME и ADMIN_PASSWORD в .env.");
        var hasher = scope.ServiceProvider.GetRequiredService<PasswordHasher<Account>>();
        db.Accounts.Add(Account.Create(credentials.Login, credentials.Name, credentials.Password, Role.Admin, hasher));
        await db.SaveChangesAsync();
    }
}
