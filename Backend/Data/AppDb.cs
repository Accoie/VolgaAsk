using Microsoft.EntityFrameworkCore;

namespace VolgaAsk;

public sealed class AppDb(DbContextOptions<AppDb> options) : DbContext(options)
{
    public DbSet<Account> Accounts => Set<Account>();
    public DbSet<Chat> Chats => Set<Chat>();
    public DbSet<Turn> Turns => Set<Turn>();

    public async Task<bool> TryCreate(Account account, CancellationToken ct)
    {
        Accounts.Add(account);
        try
        {
            await SaveChangesAsync(ct);
            return true;
        }
        catch (DbUpdateException e) when (e.InnerException is Npgsql.PostgresException { SqlState: "23505" })
        {
            return false;
        }
    }

    public Task UpgradeAccounts() => Database.ExecuteSqlRawAsync("""
        DO $$
        BEGIN
            LOCK TABLE "Accounts" IN ACCESS EXCLUSIVE MODE;
            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_schema = current_schema() AND table_name = 'Accounts' AND column_name = 'StudentId'
            ) THEN
                ALTER TABLE "Accounts" RENAME COLUMN "StudentId" TO "Login";
                ALTER INDEX "IX_Accounts_StudentId" RENAME TO "IX_Accounts_Login";
                ALTER TABLE "Accounts" ADD COLUMN "Name" text;
                UPDATE "Accounts" SET "Name" = CASE
                    WHEN "Role" = 'Admin' THEN 'Администратор'
                    ELSE 'Пользователь'
                END;
                ALTER TABLE "Accounts" ALTER COLUMN "Name" SET NOT NULL;
            END IF;
        END;
        $$;
        """);

    protected override void OnModelCreating(ModelBuilder model)
    {
        model.Entity<Account>().HasIndex(x => x.Login).IsUnique();
        model.Entity<Account>().Property(x => x.Role).HasConversion<string>();
        model.Entity<Chat>().HasOne<Account>().WithMany().HasForeignKey(x => x.OwnerId);
        model.Entity<Chat>().HasMany(x => x.Turns).WithOne().HasForeignKey(x => x.ChatId);
        model.Entity<Chat>().HasIndex(x => new { x.OwnerId, x.UpdatedAt });
    }
}
