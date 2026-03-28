DO $$
DECLARE
    parent  record;
    m       date;
    m_end   date;
    subname text;
BEGIN
    FOR parent IN
        SELECT c.relname
        FROM   pg_inherits i
        JOIN   pg_class c ON c.oid = i.inhrelid
        JOIN   pg_class p ON p.oid = i.inhparent
        WHERE  p.relname = 'statistics_userdailystats'
        ORDER  BY c.relname
    LOOP
        m := %s::date;
        WHILE m <= %s::date LOOP
            m_end   := (m + interval '1 month')::date;
            subname := parent.relname || '_' || to_char(m, 'YYYYMM');

            IF NOT EXISTS (
                SELECT 1 FROM pg_class WHERE relname = subname
            ) THEN
                EXECUTE format(
                    'CREATE TABLE %I PARTITION OF %I FOR VALUES FROM (%L) TO (%L)',
                    subname, parent.relname, m, m_end
                );
                RAISE NOTICE 'Created %', subname;
            END IF;

            m := m_end;
        END LOOP;
    END LOOP;
END
$$;
