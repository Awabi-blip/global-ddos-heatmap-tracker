CREATE TABLE IF NOT EXISTS app_users(
    id SERIAL,
    google_id TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    email CITEXT UNIQUE NOT NULL,
    created_at TIMESTAMPTZ(0) DEFAULT now(),
    total_visits INT DEFAULT 0,
    PRIMARY KEY ("id")
);

CREATE TABLE IF NOT EXISTS "countries" (
    id SERIAL,
    numeric INT, 
    country_code CHAR(2) NOT NULL UNIQUE,
    county_code_3 CHAR(3) NOT NULL UNIQUE,
    name TEXT NOT NULL UNIQUE,
    latitude DECIMAL(8,4) CHECK (latitude >= -90 AND latitude <= 90),
    longitude DECIMAL(8,4) CHECK (longitude >= -180 AND longitude <= 180),
    PRIMARY KEY("id")
);

CREATE TABLE IF NOT EXISTS abusive_ips(
    id SERIAL,
    ip_address INET NOT NULL UNIQUE,
    country_code CHAR(2),
    latitude DECIMAL(8,4) CHECK (latitude >= -90 AND latitude <= 90),
    longitude DECIMAL(8,4) CHECK (longitude >= -180 AND longitude <= 180),
    last_reported_at TIMESTAMPTZ(0) DEFAULT now(),
    PRIMARY KEY("id"),
    FOREIGN KEY country_code REFERENCES countries(country_code_2)
);


CREATE VIEW top_countries AS 
SELECT id, country_code, last_reported_at
FROM abusive_ips 
ORDER BY last_reported_at DESC
LIMIT 10000;


CREATE VIEW users_countries_view AS
SELECT abusive_ips.ip_address, abusive_ips.latitude, abusive_ips.longitude, 
countries.name as country
FROM abusive_ips 
    JOIN countries 
    ON countries.country_code = abusive_ips.country_code
ORDER BY abusive_ips.last_reported_at DESC;

-- CREATE TABLE IF NOT EXISTS "attacks" (
--     "id" SERIAL,
--     "attacker_ip_address" INET NOT NULL UNIQUE,
--     "attacker_country_alpha_2" CHAR(2) NOT NULL,
--     "attacker_latitude" DECIMAL(8,4) CHECK (attacker_latitude >= -90 AND attacker_latitude <= 90),
--     "attacker_longitude" DECIMAL(8,4) CHECK (attacker_longitude >= -180 AND attacker_longitude <= 180),
--     "seen" BOOLEAN,
--     "actor" TEXT DEFAULT NULL,
--     "sensor_count" INT,
--     "asn" TEXT,
--     "tags" TEXT[],
--     "attacked_countries" CHAR(2)[],
--     PRIMARY KEY ("id")
-- );


