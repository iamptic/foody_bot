-- scripts/seed_demo.sql
INSERT INTO restaurants (id, title, lat, lng)
VALUES ('RID_DEMO', 'DEMO Bakery', 55.751, 37.618)
ON CONFLICT (id) DO NOTHING;

INSERT INTO offers (id, restaurant_id, title, price_cents, qty_total, qty_left, expires_at)
VALUES ('OFF_DEMO_1', 'RID_DEMO', 'Набор выпечки', 35000, 10, 10, NOW() AT TIME ZONE 'UTC' + INTERVAL '90 minutes')
ON CONFLICT (id) DO NOTHING;
