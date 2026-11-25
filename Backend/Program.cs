using System.Text.Json.Serialization;
using Microsoft.AspNetCore.Authentication.Cookies;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.DataProtection;
using Microsoft.AspNetCore.Identity;
using Microsoft.EntityFrameworkCore;
using Npgsql;
using VolgaAsk;

var builder = WebApplication.CreateBuilder(args);
var services = builder.Services;
var config = builder.Configuration;
var connection = config.GetConnectionString("App") ?? new NpgsqlConnectionStringBuilder
{
    Host = "app-db", Database = "volgaask", Username = "volgaask", Password = config["DB_PASSWORD"]
}.ConnectionString;

services.AddDbContext<AppDb>(options => options.UseNpgsql(connection));
services.AddSingleton<PasswordHasher<Account>>();
services.AddSingleton<CredentialRules>();
services.AddAuthentication(CookieAuthenticationDefaults.AuthenticationScheme).AddCookie(Auth.Configure);
services.AddAuthorization(options => options.FallbackPolicy = new AuthorizationPolicyBuilder()
    .RequireAuthenticatedUser().Build());
services.AddDataProtection().PersistKeysToFileSystem(new DirectoryInfo(config["KEYS_DIR"] ?? "/app/keys"));
services.AddRateLimiter(options =>
{
    options.RejectionStatusCode = 429;
    options.AddPolicy("login", context => System.Threading.RateLimiting.RateLimitPartition.GetFixedWindowLimiter(
        context.Connection.RemoteIpAddress?.ToString() ?? "local", _ => new()
        {
            PermitLimit = 60, Window = TimeSpan.FromMinutes(1)
        }));
});
services.AddControllers().AddJsonOptions(options => options.JsonSerializerOptions.Converters.Add(
    new JsonStringEnumConverter(allowIntegerValues: false)));
services.AddSwaggerGen();

var app = builder.Build();
await Auth.Initialize(app.Services, config);
app.UseExceptionHandler(handler => handler.Run(async ctx =>
{
    ctx.Response.StatusCode = StatusCodes.Status502BadGateway;
    await ctx.Response.WriteAsJsonAsync(new { detail = "Не удалось выполнить запрос к сервису." });
}));
app.UseSwagger();
app.UseSwaggerUI();
app.UseRouting();
app.UseRateLimiter();
app.UseAuthentication();
app.UseAuthorization();
app.MapControllers();
app.Run();
