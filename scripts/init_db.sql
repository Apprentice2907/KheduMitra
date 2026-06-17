-- Run this script in your Supabase SQL Editor to initialize Phase 4 tables.

-- Enable pgvector extension (if not already enabled in Phase 2)
CREATE EXTENSION IF NOT EXISTS vector;

-- Farmers table for subscriptions
CREATE TABLE IF NOT EXISTS farmers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    phone_number VARCHAR(15) UNIQUE NOT NULL,
    state VARCHAR(50),
    district VARCHAR(50),
    crops_grown TEXT[],
    language VARCHAR(10) DEFAULT 'hi',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now())
);

-- Mandi Prices table (populated by GH Actions scraper)
CREATE TABLE IF NOT EXISTS mandi_prices (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    state VARCHAR(50) NOT NULL,
    district VARCHAR(50) NOT NULL,
    commodity VARCHAR(100) NOT NULL,
    min_price NUMERIC,
    max_price NUMERIC,
    modal_price NUMERIC,
    arrival_date DATE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()),
    UNIQUE(state, district, commodity, arrival_date)
);

-- Fertilizer Prices table (populated by GH Actions scraper)
CREATE TABLE IF NOT EXISTS fertilizer_prices (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    fertilizer_type VARCHAR(50) NOT NULL, -- e.g., 'DAP', 'Urea', 'MOP'
    price_per_bag NUMERIC NOT NULL,
    source_url TEXT,
    recorded_at DATE NOT NULL DEFAULT CURRENT_DATE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()),
    UNIQUE(fertilizer_type, recorded_at)
);

-- Call Logs table (for future analytics)
CREATE TABLE IF NOT EXISTS call_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    call_sid VARCHAR(50) UNIQUE NOT NULL,
    phone_number VARCHAR(15) NOT NULL,
    intent VARCHAR(50),
    query_text TEXT,
    response_text TEXT,
    duration_seconds INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now())
);

-- Create simple indices for fast lookups
CREATE INDEX IF NOT EXISTS idx_farmers_district ON farmers(district);
CREATE INDEX IF NOT EXISTS idx_mandi_lookup ON mandi_prices(state, district, commodity);
