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
var kbConnection = config["KB_CONNECTION"] ?? new NpgsqlConnectionStringBuilder
{
    Host = "pgvector", Database = "rag_service", Username = "rag_service",
    Password = config["KB_PASSWORD"] ?? throw new InvalidOperationException("Set KB_PASSWORD.")
}.ConnectionString;
services.AddDbContext<KbStore>(options => options.UseNpgsql(kbConnection));
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
services.AddHttpClient<RagClient>(client =>
{
    client.BaseAddress = new Uri(config["RAG_URL"] ?? "http://rag:8000");
    client.Timeout = TimeSpan.FromMinutes(12);
});
foreach (var service in new[] { "generator", "reviewer" })
    services.AddHttpClient(service, client =>
    {
        client.BaseAddress = new Uri($"http://{service}:8000");
        client.Timeout = TimeSpan.FromMinutes(10);
    });
services.AddScoped<Documents>();
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
