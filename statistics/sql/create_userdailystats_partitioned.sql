-- Partitioned table: statistics_userdailystats
-- Level 1: RANGE on user_id (buckets of 5000)
-- Level 2: RANGE on period (monthly)

CREATE TABLE statistics_userdailystats (
    user_id   integer       NOT NULL,
    period    date          NOT NULL,
    hexagons_acquired integer NOT NULL DEFAULT 0,
    computed_at timestamptz  NOT NULL DEFAULT now(),
    PRIMARY KEY (user_id, period)
) PARTITION BY RANGE (user_id);

-- Level 1 partitions (by user_id range)
CREATE TABLE statistics_userdailystats_u0
    PARTITION OF statistics_userdailystats
    FOR VALUES FROM (0) TO (5000)
    PARTITION BY RANGE (period);

CREATE TABLE statistics_userdailystats_u5000
    PARTITION OF statistics_userdailystats
    FOR VALUES FROM (5000) TO (10000)
    PARTITION BY RANGE (period);

CREATE TABLE statistics_userdailystats_u10000
    PARTITION OF statistics_userdailystats
    FOR VALUES FROM (10000) TO (15000)
    PARTITION BY RANGE (period);

-- Level 2 sub-partitions (monthly) for u0
CREATE TABLE statistics_userdailystats_u0_202603
    PARTITION OF statistics_userdailystats_u0
    FOR VALUES FROM ('2026-03-01') TO ('2026-04-01');
CREATE TABLE statistics_userdailystats_u0_202604
    PARTITION OF statistics_userdailystats_u0
    FOR VALUES FROM ('2026-04-01') TO ('2026-05-01');
CREATE TABLE statistics_userdailystats_u0_202605
    PARTITION OF statistics_userdailystats_u0
    FOR VALUES FROM ('2026-05-01') TO ('2026-06-01');
CREATE TABLE statistics_userdailystats_u0_202606
    PARTITION OF statistics_userdailystats_u0
    FOR VALUES FROM ('2026-06-01') TO ('2026-07-01');

-- Level 2 sub-partitions (monthly) for u5000
CREATE TABLE statistics_userdailystats_u5000_202603
    PARTITION OF statistics_userdailystats_u5000
    FOR VALUES FROM ('2026-03-01') TO ('2026-04-01');
CREATE TABLE statistics_userdailystats_u5000_202604
    PARTITION OF statistics_userdailystats_u5000
    FOR VALUES FROM ('2026-04-01') TO ('2026-05-01');
CREATE TABLE statistics_userdailystats_u5000_202605
    PARTITION OF statistics_userdailystats_u5000
    FOR VALUES FROM ('2026-05-01') TO ('2026-06-01');
CREATE TABLE statistics_userdailystats_u5000_202606
    PARTITION OF statistics_userdailystats_u5000
    FOR VALUES FROM ('2026-06-01') TO ('2026-07-01');

-- Level 2 sub-partitions (monthly) for u10000
CREATE TABLE statistics_userdailystats_u10000_202603
    PARTITION OF statistics_userdailystats_u10000
    FOR VALUES FROM ('2026-03-01') TO ('2026-04-01');
CREATE TABLE statistics_userdailystats_u10000_202604
    PARTITION OF statistics_userdailystats_u10000
    FOR VALUES FROM ('2026-04-01') TO ('2026-05-01');
CREATE TABLE statistics_userdailystats_u10000_202605
    PARTITION OF statistics_userdailystats_u10000
    FOR VALUES FROM ('2026-05-01') TO ('2026-06-01');
CREATE TABLE statistics_userdailystats_u10000_202606
    PARTITION OF statistics_userdailystats_u10000
    FOR VALUES FROM ('2026-06-01') TO ('2026-07-01');
