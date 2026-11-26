using Microsoft.EntityFrameworkCore;

namespace VolgaAsk;

public sealed record KbDocument(Guid Id, string Title, string Filename, DateOnly? Date, string Status,
    string? ErrorCode, bool OcrApplied);
public sealed record PortalDocument(string Url, string Title, string Filename, string? Checksum, bool InLibrary,
    bool OtherCopy);
public sealed record PortalSync(DateTime? Refreshed, string? Error);

public sealed class KbStore(DbContextOptions<KbStore> options) : DbContext(options)
{
    public Task<List<KbDocument>> Documents(CancellationToken ct) => Database.SqlQuery<KbDocument>($"""
        SELECT id AS "Id", title AS "Title", filename AS "Filename", document_date AS "Date",
               status AS "Status", error_code AS "ErrorCode", ocr_applied AS "OcrApplied"
        FROM kb_documents ORDER BY created_at DESC
        """).ToListAsync(ct);

    public Task<List<PortalDocument>> Catalog(CancellationToken ct) => Database.SqlQuery<PortalDocument>($"""
        SELECT c.url AS "Url", c.title AS "Title", c.filename AS "Filename", c.checksum AS "Checksum",
            EXISTS(SELECT 1 FROM kb_documents d WHERE d.checksum=c.checksum AND d.status<>'failed') AS "InLibrary",
            EXISTS(SELECT 1 FROM kb_documents d WHERE d.status='ready' AND d.checksum<>c.checksum
                AND (d.source=c.url OR lower(d.filename)=lower(c.filename))) AS "OtherCopy"
        FROM kb_catalog c WHERE c.available ORDER BY c.title
        """).ToListAsync(ct);

    public Task<PortalSync?> Sync(CancellationToken ct) => Database.SqlQuery<PortalSync>($"""
        SELECT refreshed AS "Refreshed", error AS "Error" FROM kb_sync
        """).FirstOrDefaultAsync(ct);

    public Task<int> Import(Guid id, string url, string checksum, CancellationToken ct) =>
        Database.ExecuteSqlInterpolatedAsync($"""
            INSERT INTO kb_documents(id,title,filename,checksum,source,status)
            SELECT {id},title,filename,checksum,url,'queued' FROM kb_catalog
            WHERE url={url} AND available AND checksum={checksum} ON CONFLICT DO NOTHING
            """, ct);

    public Task<int> Upload(Guid id, string title, string filename, DateOnly date, string hash, byte[] pdf, CancellationToken ct) =>
        Database.ExecuteSqlInterpolatedAsync($"""
            INSERT INTO kb_documents(id,title,filename,document_date,checksum,status,payload)
            VALUES ({id},{title},{filename},{date},{hash},'queued',{pdf}) ON CONFLICT DO NOTHING
            """, ct);

    public async Task<int> Delete(Guid id, CancellationToken ct)
    {
        var removed = await Database.ExecuteSqlInterpolatedAsync($"DELETE FROM kb_documents WHERE id={id} AND status='failed'", ct);
        if (removed == 1) return removed;
        return await Database.ExecuteSqlInterpolatedAsync($"""
        UPDATE kb_documents SET status='deleting' WHERE id={id} AND status='ready'
        """, ct);
    }
}
