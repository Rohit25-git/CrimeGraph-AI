import os
import json
import csv
import random
from datetime import datetime, timedelta

# Create directories
os.makedirs("C:/Users/Rohit/OneDrive/Documents/Desktop/SIH26/data/fir", exist_ok=True)
os.makedirs("C:/Users/Rohit/OneDrive/Documents/Desktop/SIH26/data/cdr", exist_ok=True)
os.makedirs("C:/Users/Rohit/OneDrive/Documents/Desktop/SIH26/data/financial", exist_ok=True)
os.makedirs("C:/Users/Rohit/OneDrive/Documents/Desktop/SIH26/data/surveillance", exist_ok=True)
os.makedirs("C:/Users/Rohit/OneDrive/Documents/Desktop/SIH26/data/intelligence", exist_ok=True)

# Define constants
DATA_DIR = "C:/Users/Rohit/OneDrive/Documents/Desktop/SIH26/data"

def generate_data():
    # 1. Generate 110 Persons
    first_names = ["Arjun", "Ravi", "Sameer", "Vikram", "Neha", "Rahul", "Priya", "Amit", "Sanjay", "Anjali", 
                   "Karan", "Simran", "Kabir", "Meera", "Rohit", "Deepa", "Sunil", "Kiran", "Vijay", "Aisha",
                   "Raj", "Pooja", "Varun", "Rhea", "Manish", "Aditi", "Alok", "Divya", "Gaurav", "Shreya",
                   "Tushar", "Siddharth", "Aman", "Rohan", "Ritu", "Sneha", "Kunal", "Tanvi", "Abhishek", "Prerna"]
    last_names = ["Mehta", "Sharma", "Khan", "Das", "Patel", "Verma", "Sen", "Gupta", "Joshi", "Roy",
                  "Malhotra", "Kapoor", "Singh", "Reddy", "Nair", "Bose", "Choudhury", "Mishra", "Dubey", "Yadav",
                  "Dwivedi", "Trivedi", "Pathak", "Chawla", "Sareen", "Mehra", "Oberoi", "Vance", "Grover", "Rao"]
    
    persons = []
    # Seed specific nodes for the demo scenario
    persons.append({"id": "P001", "name": "Arjun Mehta", "type": "PERSON", "properties": {"occupation": "Exporter", "age": 42}})
    persons.append({"id": "P002", "name": "Ravi Sharma", "type": "PERSON", "properties": {"occupation": "Logistics Manager", "age": 38}})
    persons.append({"id": "P003", "name": "Sameer Khan", "type": "PERSON", "properties": {"occupation": "Financial Advisor", "age": 45}})
    persons.append({"id": "P004", "name": "Vikram Das", "type": "PERSON", "properties": {"occupation": "Warehouse Supervisor", "age": 31}})
    
    used_names = {"Arjun Mehta", "Ravi Sharma", "Sameer Khan", "Vikram Das"}
    p_idx = 5
    while len(persons) < 110:
        name = f"{random.choice(first_names)} {random.choice(last_names)}"
        if name not in used_names:
            used_names.add(name)
            pid = f"P{p_idx:03d}"
            persons.append({
                "id": pid,
                "name": name,
                "type": "PERSON",
                "properties": {
                    "occupation": random.choice(["Business", "Consultant", "Trader", "Accountant", "Driver", "Agent", "Advisor", "Logistics", "Associate"]),
                    "age": random.randint(23, 62)
                }
            })
            p_idx += 1

    # 2. Generate 60 Phone Numbers
    phones = []
    phones.append({"id": "PH001", "number": "+91-98200-11111", "type": "PHONE", "properties": {"carrier": "Jio", "status": "active"}})
    phones.append({"id": "PH002", "number": "+91-98200-22222", "type": "PHONE", "properties": {"carrier": "Airtel", "status": "active"}})
    phones.append({"id": "PH003", "number": "+91-98200-33333", "type": "PHONE", "properties": {"carrier": "Vi", "status": "suspended"}})
    
    for i in range(4, 61):
        phones.append({
            "id": f"PH{i:03d}",
            "number": f"+91-98200-{random.randint(10000, 99999)}",
            "type": "PHONE",
            "properties": {"carrier": random.choice(["Jio", "Airtel", "Vi"]), "status": "active"}
        })

    # 3. Generate 40 Vehicles
    vehicles = []
    vehicles.append({"id": "V001", "plate": "MH-01-AB-1234", "type": "VEHICLE", "properties": {"model": "Toyota Fortuner", "color": "Black"}})
    vehicles.append({"id": "V002", "plate": "MH-02-CD-5678", "type": "VEHICLE", "properties": {"model": "Honda City", "color": "White"}})
    for i in range(3, 41):
        vehicles.append({
            "id": f"V{i:03d}",
            "plate": f"MH-{random.randint(1, 14):02d}-{chr(random.randint(65, 90))}{chr(random.randint(65, 90))}-{random.randint(1000, 9999)}",
            "type": "VEHICLE",
            "properties": {
                "model": random.choice(["Hyundai Creta", "Maruti Swift", "Mahindra Thar", "Tata Nexon", "Kia Seltos", "Toyota Innova"]),
                "color": random.choice(["Grey", "Red", "Blue", "Black", "Silver", "White"])
            }
        })

    # 4. Generate 40 Locations
    locations = []
    locations.append({"id": "LOC001", "name": "Warehouse A (Port Trust)", "type": "LOCATION", "properties": {"city": "Mumbai", "coordinates": "18.95,72.84"}})
    locations.append({"id": "LOC002", "name": "Safehouse B (Bandra)", "type": "LOCATION", "properties": {"city": "Mumbai", "coordinates": "19.05,72.83"}})
    locations.append({"id": "LOC003", "name": "Customs Checkpoint", "type": "LOCATION", "properties": {"city": "Nhava Sheva", "coordinates": "18.90,72.95"}})
    for i in range(4, 41):
        locations.append({
            "id": f"LOC{i:03d}",
            "name": f"Location {chr(random.randint(65, 90))} ({random.choice(['Terminal', 'Office', 'Apartment', 'Parking', 'Warehouse', 'Resort'])} )",
            "type": "LOCATION",
            "properties": {
                "city": random.choice(["Mumbai", "Navi Mumbai", "Thane", "Pune", "Goa", "Delhi"]),
                "coordinates": f"{round(random.uniform(18.8, 19.3), 4)},{round(random.uniform(72.7, 73.1), 4)}"
            }
        })

    # 5. Generate 18 Organizations
    organizations = []
    organizations.append({"id": "ORG001", "name": "Mehta Exports Ltd", "type": "ORGANIZATION", "properties": {"sector": "Export-Import", "reg_no": "EXP-10928"}})
    organizations.append({"id": "ORG002", "name": "Sharma Logistics Solutions", "type": "ORGANIZATION", "properties": {"sector": "Freight & Transport", "reg_no": "LOG-58291"}})
    organizations.append({"id": "ORG003", "name": "Khan FinCorp", "type": "ORGANIZATION", "properties": {"sector": "Wealth Management", "reg_no": "FIN-29481"}})
    for i in range(4, 19):
        organizations.append({
            "id": f"ORG{i:03d}",
            "name": f"{random.choice(last_names)} Logistics" if i%2==0 else f"{random.choice(last_names)} FinCorp",
            "type": "ORGANIZATION",
            "properties": {
                "sector": random.choice(["Shell Corporation", "Freight Transport", "Retail Distribution", "Financial Services"]),
                "reg_no": f"REG-{random.randint(10000, 99999)}"
            }
        })

    # Save to JSON Files
    with open(f"{DATA_DIR}/persons.json", "w") as f:
        json.dump(persons, f, indent=2)
    with open(f"{DATA_DIR}/phones.json", "w") as f:
        json.dump(phones, f, indent=2)
    with open(f"{DATA_DIR}/vehicles.json", "w") as f:
        json.dump(vehicles, f, indent=2)
    with open(f"{DATA_DIR}/locations.json", "w") as f:
        json.dump(locations, f, indent=2)
    with open(f"{DATA_DIR}/organizations.json", "w") as f:
        json.dump(organizations, f, indent=2)

    # 6. Relationships (500+)
    # Build relationships carefully.
    relations = []
    base_date = datetime.now() - timedelta(days=30)

    # We must ensure P001 has exactly 17 connections to align with the Phase 1 UI demo:
    # 4 Persons: P002 (Ravi), P003 (Sameer), P005, P006
    # 2 Phones: PH001 (own), PH002 (uses)
    # 2 Vehicles: V001, V002
    # 2 Locations: LOC001, LOC002
    # 2 Orgs: ORG001, ORG002
    # 5 other Persons via calls/transfers: P007, P008, P009, P010, P011
    # Total unique connections: 17.
    relations.append({"source": "P001", "target": "PH001", "type": "USES", "timestamp": (base_date + timedelta(days=1)).isoformat(), "amount": 0})
    relations.append({"source": "P001", "target": "PH002", "type": "USES", "timestamp": (base_date + timedelta(days=2)).isoformat(), "amount": 0})
    relations.append({"source": "P001", "target": "V001", "type": "OWNS", "timestamp": (base_date + timedelta(days=1)).isoformat(), "amount": 0})
    relations.append({"source": "P001", "target": "V002", "type": "ASSOCIATED_WITH", "timestamp": (base_date + timedelta(days=3)).isoformat(), "amount": 0})
    relations.append({"source": "P001", "target": "LOC001", "type": "VISITED", "timestamp": (base_date + timedelta(days=4)).isoformat(), "amount": 0})
    relations.append({"source": "P001", "target": "LOC002", "type": "VISITED", "timestamp": (base_date + timedelta(days=5)).isoformat(), "amount": 0})
    relations.append({"source": "P001", "target": "ORG001", "type": "WORKS_FOR", "timestamp": (base_date + timedelta(days=1)).isoformat(), "amount": 0})
    relations.append({"source": "P001", "target": "ORG002", "type": "ASSOCIATED_WITH", "timestamp": (base_date + timedelta(days=2)).isoformat(), "amount": 0})
    
    relations.append({"source": "P001", "target": "P002", "type": "CALLED", "timestamp": (base_date + timedelta(days=6)).isoformat(), "amount": 0})
    relations.append({"source": "P001", "target": "P003", "type": "CALLED", "timestamp": (base_date + timedelta(days=7)).isoformat(), "amount": 0})
    relations.append({"source": "P001", "target": "P005", "type": "CALLED", "timestamp": (base_date + timedelta(days=8)).isoformat(), "amount": 0})
    relations.append({"source": "P001", "target": "P006", "type": "MESSAGED", "timestamp": (base_date + timedelta(days=9)).isoformat(), "amount": 0})
    relations.append({"source": "P001", "target": "P007", "type": "CALLED", "timestamp": (base_date + timedelta(days=10)).isoformat(), "amount": 0})
    relations.append({"source": "P001", "target": "P008", "type": "CALLED", "timestamp": (base_date + timedelta(days=11)).isoformat(), "amount": 0})
    relations.append({"source": "P001", "target": "P009", "type": "MESSAGED", "timestamp": (base_date + timedelta(days=12)).isoformat(), "amount": 0})
    relations.append({"source": "P001", "target": "P010", "type": "CALLED", "timestamp": (base_date + timedelta(days=13)).isoformat(), "amount": 0})
    relations.append({"source": "P001", "target": "P011", "type": "TRANSFERRED_TO", "timestamp": (base_date + timedelta(days=14)).isoformat(), "amount": 50000})

    # Now generate communication links (CALLED, MESSAGED) dense in 3 communities (300+ links)
    # Community 1: P005 - P035 (30 persons)
    # Community 2: P036 - P070 (35 persons)
    # Community 3: P071 - P110 (40 persons)
    # Make sure we don't connect to P001 to keep P001 connections capped at exactly 17.
    
    for i in range(320):
        r = random.random()
        if r < 0.4:
            src = random.choice([f"P{x:03d}" for x in range(5, 36)])
            tgt = random.choice([f"P{x:03d}" for x in range(5, 36)])
        elif r < 0.7:
            src = random.choice([f"P{x:03d}" for x in range(36, 71)])
            tgt = random.choice([f"P{x:03d}" for x in range(36, 71)])
        else:
            src = random.choice([f"P{x:03d}" for x in range(71, 110)])
            tgt = random.choice([f"P{x:03d}" for x in range(71, 110)])
            
        if src != tgt:
            ts = base_date + timedelta(days=random.randint(1, 28), hours=random.randint(0, 23), minutes=random.randint(0, 59))
            relations.append({
                "source": src,
                "target": tgt,
                "type": random.choice(["CALLED", "MESSAGED"]),
                "timestamp": ts.isoformat(),
                "amount": 0
            })

    # Generate phone mappings (USES)
    for x in range(1, 61):
        pid = f"P{random.randint(2, 109):03d}"
        phid = f"PH{x:03d}"
        if phid not in ["PH001", "PH002"]:  # Keep P001 clean
            relations.append({
                "source": pid,
                "target": phid,
                "type": "USES",
                "timestamp": (base_date + timedelta(days=random.randint(1, 10))).isoformat(),
                "amount": 0
            })

    # Generate Financial Transactions (120+)
    for i in range(130):
        src = random.choice([f"P{x:03d}" for x in range(2, 110)])
        tgt = random.choice([f"P{x:03d}" for x in range(2, 110)])
        if src != tgt:
            ts = base_date + timedelta(days=random.randint(1, 28), hours=random.randint(0, 23))
            relations.append({
                "source": src,
                "target": tgt,
                "type": "TRANSFERRED_TO",
                "timestamp": ts.isoformat(),
                "amount": random.randint(1000, 25000)
            })

    # Generate Location visits (100+)
    for i in range(110):
        src = random.choice([f"P{x:03d}" for x in range(2, 110)])
        tgt = random.choice([f"LOC{x:03d}" for x in range(1, 41)])
        ts = base_date + timedelta(days=random.randint(1, 28), hours=random.randint(8, 21))
        relations.append({
            "source": src,
            "target": tgt,
            "type": "VISITED",
            "timestamp": ts.isoformat(),
            "amount": 0
        })

    # Vehicle ownerships (40+)
    for x in range(1, 41):
        pid = f"P{random.randint(2, 109):03d}"
        vid = f"V{x:03d}"
        if vid not in ["V001", "V002"]:
            relations.append({
                "source": pid,
                "target": vid,
                "type": "OWNS",
                "timestamp": (base_date + timedelta(days=random.randint(1, 10))).isoformat(),
                "amount": 0
            })

    # Organization WORKS_FOR / ASSOCIATED_WITH relationships (30+)
    for x in range(1, 19):
        pid = f"P{random.randint(2, 109):03d}"
        oid = f"ORG{x:03d}"
        if oid not in ["ORG001", "ORG002"]:
            relations.append({
                "source": pid,
                "target": oid,
                "type": random.choice(["WORKS_FOR", "ASSOCIATED_WITH"]),
                "timestamp": (base_date + timedelta(days=random.randint(1, 5))).isoformat(),
                "amount": 0
            })

    # 7. INTENTIONAL ANOMALIES & BRIDGES Setup:
    # Anomaly 1: Financial Outlier
    # P003 (Sameer) transfers massive funds to P002 (Ravi Sharma)
    relations.append({
        "source": "P003",
        "target": "P002",
        "type": "TRANSFERRED_TO",
        "timestamp": (base_date + timedelta(days=15, hours=10)).isoformat(),
        "amount": 1500000
    })
    
    # Anomaly 2: Circular Transactions (Cycle: P005 -> P006 -> P007 -> P005)
    relations.append({"source": "P005", "target": "P006", "type": "TRANSFERRED_TO", "timestamp": (base_date + timedelta(days=16)).isoformat(), "amount": 80000})
    relations.append({"source": "P006", "target": "P007", "type": "TRANSFERRED_TO", "timestamp": (base_date + timedelta(days=17)).isoformat(), "amount": 80000})
    relations.append({"source": "P007", "target": "P005", "type": "TRANSFERRED_TO", "timestamp": (base_date + timedelta(days=18)).isoformat(), "amount": 80000})
    
    # Anomaly 3: Sudden Communication Spike
    # P004 (Vikram) has 12 outgoing calls/messages to 10 different people on a single day
    for x in range(10, 20):
        relations.append({
            "source": "P004",
            "target": f"P{x:03d}",
            "type": "CALLED",
            "timestamp": (base_date + timedelta(days=20, hours=random.randint(9, 18))).isoformat(),
            "amount": 0
        })
        
    # Anomaly 4: Location overlap
    # P002 (Ravi Sharma) and P003 (Sameer Khan) meet at LOC001 on August 12
    relations.append({
        "source": "P002",
        "target": "LOC001",
        "type": "VISITED",
        "timestamp": (base_date + timedelta(days=12, hours=14, minutes=10)).isoformat(),
        "amount": 0
    })
    relations.append({
        "source": "P003",
        "target": "LOC001",
        "type": "VISITED",
        "timestamp": (base_date + timedelta(days=12, hours=14, minutes=45)).isoformat(),
        "amount": 0
    })

    # Anomaly 5: Rapid Network Expansion
    # P020 connects to 8 new people within 48 hours
    for x in range(50, 58):
        relations.append({
            "source": "P020",
            "target": f"P{x:03d}",
            "type": "CALLED",
            "timestamp": (base_date + timedelta(days=22, hours=random.randint(1, 23))).isoformat(),
            "amount": 0
        })

    # Anomaly 6: Unusual Temporal Activity
    # P030 performs a transfer of funds at 2:34 AM
    relations.append({
        "source": "P030",
        "target": "P035",
        "type": "TRANSFERRED_TO",
        "timestamp": (base_date + timedelta(days=23, hours=2, minutes=34)).isoformat(),
        "amount": 125000
    })

    # Save all relationships in a CSV
    with open(f"{DATA_DIR}/relationships.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["source_id", "target_id", "rel_type", "timestamp", "amount"])
        for r in relations:
            writer.writerow([r["source"], r["target"], r["type"], r["timestamp"], r["amount"]])

    # 8. Create fictional narrative Intelligence Report
    report_text = """
    INTELLIGENCE REPORT: OPERATION MONSOON
    DATE: August 12, 2026
    CLASSIFICATION: CONFIDENTIAL - INVESTIGATOR DECISION SUPPORT
    
    SUMMARY OF OBSERVATIONS:
    Subject Arjun Mehta (P001) was observed entering Mehta Exports Ltd (ORG001) in Mumbai. 
    Arjun later met Ravi Sharma (P002) at Bandra Safehouse B (LOC002) at 12 August 2026. 
    Ravi Sharma (P002) later contacted Sameer Khan (P003) using phone number +91-98200-22222.
    Sameer Khan (P003) is suspected of handling transaction transfers for Khan FinCorp (ORG003).
    Arjun Mehta (P001) was seen near vehicle MH-01-AB-1234 (V001) parked near Port Trust Warehouse A (LOC001).
    A transfer of funds was registered involving account ACC003 (held by Khan FinCorp) transferring INR 1,500,000 to Ravi Sharma.
    
    RECOMMENDATION:
    Indicators require human review and further corroboration through CDR analysis and audit logs.
    """
    
    with open(f"{DATA_DIR}/intelligence/intel_report_01.txt", "w") as f:
        f.write(report_text)
        
    print(f"Large Demo data (500+ relationships) generated successfully in {DATA_DIR}!")

if __name__ == "__main__":
    generate_data()
