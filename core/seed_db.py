import os
from core.db import DB_PATH, init_db, get_connection

def reset_db():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
        print("🗑️ Old database removed.")
    init_db()
    print("✅ Database schema initialized.")


def seed_data():
    conn = get_connection()
    c = conn.cursor()

    # Users
    c.execute("INSERT INTO users (name, email, phone) VALUES (?, ?, ?)",
              ("Demo User", "demo@example.com", "+916301989290"))

    # Policies
    policies = [
        ("Health Basic", "health", 5000, "Covers hospitalization up to ₹2,00,000", 200000, 0, 1),
        ("Health Premium", "health", 12000, "Covers hospitalization up to ₹5,00,000 + maternity benefits", 500000, 0, 1),
        ("Vehicle Standard", "vehicle", 8000, "Covers accidental damage + third-party liability", 300000, 0, 1),
        ("Vehicle Comprehensive", "vehicle", 15000, "Covers damage, theft, fire + personal accident cover", 700000, 0, 1),
        ("Health Inactive", "health", 8000, "Old inactive policy", 100000, 0, 0),
    ]
    c.executemany("INSERT INTO policies (name, type, premium, benefits, coverage_limit, is_custom, is_active) VALUES (?, ?, ?, ?, ?, ?, ?)", policies)

    # Health Insurance for Demo User
    c.execute("INSERT INTO user_health_insurance (user_id, policy_id, status) VALUES (?, ?, ?)", (1, 2, "active"))

    # Vehicle Insurance for Demo User
    c.execute("""
        INSERT INTO user_vehicle_insurance (user_id, policy_id, number_plate, vehicle_type, brand_model, age, kms_driven, wheels, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (1, 4, "TS09AB1234", "car", "Hyundai Creta", 3, 35000, 4, "active"))

    conn.commit()
    conn.close()
    print("✅ Sample users, policies, and insurances seeded.")


if __name__ == "__main__":
    reset_db()
    seed_data()
    print("🎉 Database ready with new schema + seed data!")
