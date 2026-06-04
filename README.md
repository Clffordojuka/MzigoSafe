# MzigoSafe

**MzigoSafe** is an offline-first, USSD-based logistics escrow platform designed to eliminate the trust deficit in the informal e-commerce sector. By leveraging a centralized ledger, a strict **Dual-OTP Chain of Custody**, and a dedicated data warehousing pipeline, MzigoSafe mathematically guarantees proof-of-delivery, instant M-Pesa payouts, and analytical insights for logistics optimization.

---

## 🚀 The Problem

The informal logistics market is crippled by a lack of trust:

* **Sellers** refuse to dispatch goods without upfront payment.
* **Buyers** refuse to pay before physically inspecting the item.
* **Both parties** fear the delivery rider might disappear with the package or the cash.

Current logistics applications require smartphones, active internet connections, and complex onboarding, alienating a massive portion of the market that relies on feature phones and USSD infrastructure.

## ✨ The Solution & Core Features

MzigoSafe operates entirely over USSD (`*384*...#`) and SMS, making it accessible to 100% of mobile users with zero data requirements.

* **Live M-Pesa Escrow:** Funds are securely locked in the system via Safaricom STK Push before a rider is ever dispatched.
* **Dual-OTP Verification:** The system generates two unique SMS OTPs. The rider cannot progress the delivery or get paid without physically collecting the **Pickup OTP** from the seller and the **Delivery OTP** from the buyer.
* **Universal Order Tracking:** Buyers and sellers can instantly check the real-time status of their package directly from the main menu using their phone number—no tracking IDs required.
* **Stateful USSD Engine:** Powered by a PostgreSQL session manager, the menus are fully crash-proof, remembering user states even if a session drops.
* **Reverse Logistics & Dispute Resolution:** Built-in flows allow riders to log buyer rejections at the door, automatically triggering item refunds to the buyer while securing the transit fee for the rider.

---

## 💸 Financial Architecture (Daraja API)

MzigoSafe utilizes an asynchronous event-driven architecture to handle Safaricom's Daraja API, ensuring no funds are lost during network timeouts.

```mermaid
sequenceDiagram
    participant B as Buyer
    participant S as Seller
    participant R as Rider
    participant M as MzigoSafe API
    participant D as Daraja (Safaricom)

    Note over B,M: 1. Escrow Lock (C2B)
    B->>M: Approves Escrow via USSD
    M->>D: Trigger STK Push Request
    D-->>B: PIN Prompt on Phone
    B->>D: Enters M-Pesa PIN
    D-->>M: Asynchronous Webhook (Success)
    M->>M: Secure Ledger & Generate OTPs

    Note over R,M: 2. Automated Payouts (B2C)
    R->>M: Inputs Delivery OTP at Drop-off
    M->>M: Verify OTP & Break Escrow
    M->>D: B2C API (Item Price)
    D-->>S: Instant M-Pesa Deposit
    M->>D: B2C API (Delivery Fee)
    D-->>R: Instant M-Pesa Deposit

```

---

## 📊 Analytics & Data Warehousing (OLAP Engine)

To prevent analytical queries from slowing down live USSD operations, MzigoSafe decouples its transactional records from its business intelligence engine. An automated ETL pipeline extracts live data into a dedicated **Star Schema** optimized for column aggregation and Machine Learning training.

```mermaid
erDiagram
    FACT_DELIVERIES {
        int fact_id PK
        int delivery_id
        int date_id FK
        int seller_id FK
        int rider_id FK
        float item_price
        float delivery_fee
        float time_to_pickup_minutes
        float time_to_delivery_minutes
        string status
    }
    DIM_USERS {
        int user_id PK
        string phone_number
        string role
        date date_joined
    }
    DIM_TIME {
        int date_id PK
        date full_date
        int year
        int month
        int day
        string day_of_week
        boolean is_weekend
    }
    DIM_USERS ||--o{ FACT_DELIVERIES : "acts as seller/rider"
    DIM_TIME ||--o{ FACT_DELIVERIES : "timestamps order"

```

### Analytical Capabilities

* **Nightly ETL Processing:** Executing `python etl_pipeline.py` extracts new, closed transactions, computes operational delivery and pickup durations (ETAs), maps datetime dimensions, and loads them cleanly into the warehouse.
* **Downstream Integration:** The OLAP engine exposes structured Pandas dataframes, ready to pipe directly into Power BI dashboards or train advanced tree-based regression models.

---

## 🛠️ Technical Architecture

### Tech Stack

* **Backend API:** Python, FastAPI
* **Database & ORM:** PostgreSQL, SQLAlchemy (with manual schema migrations via SQL injections)
* **Data Science & Analytics:** Pandas, LightGBM, Scikit-Learn
* **Telecommunications:** Africa's Talking API (USSD & SMS)
* **Payments:** Safaricom Daraja API (M-Pesa Express & B2C)

### Core System Flow

| Phase | Actor | Action | Database State |
| --- | --- | --- | --- |
| **1. Initiation** | Seller | Dials USSD, inputs Buyer number, item price, and delivery fee. | `pending_buyer_payment` |
| **2. Escrow Trap** | Buyer | Dials USSD, STK Push triggers on phone. Webhook confirms payment. | `funds_secured` (OTPs sent) |
| **3. Dispatch & Pickup** | Rider | Accepts job via USSD, travels to Seller, inputs **Pickup OTP**. | `in_transit` |
| **4. Handover & Payout** | Rider | Hands package to Buyer, inputs **Delivery OTP**. | `delivered` (B2C Payouts fired) |
| **5. Dispute (Edge Case)** | Rider | Reports buyer rejection at drop-off. | `cancelled` (Refund issued) |

---

## 💻 Local Development Setup

### Prerequisites

* Python 3.8+
* PostgreSQL
* Africa's Talking Sandbox Account
* Safaricom Daraja Developer Account

### Installation

1. **Clone the repository:**

```bash
git clone https://github.com/yourusername/mzigosafe.git
cd mzigosafe

```

2. **Create a virtual environment and install dependencies:**

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

```

3. **Environment Variables:**
Create a `.env` file in the root directory and populate your API credentials:

```env
DATABASE_URL=postgresql://username:password@localhost:5432/mzigosafe_db

# Africa's Talking
AT_USERNAME=sandbox
AT_API_KEY=your_sandbox_api_key

# Safaricom Daraja (M-Pesa)
MPESA_CONSUMER_KEY=your_key
MPESA_CONSUMER_SECRET=your_secret
MPESA_PASSKEY=your_passkey
MPESA_SHORTCODE=174379
MPESA_B2C_SHORTCODE=600986
MPESA_B2C_INITIATOR_NAME=testapi
MPESA_B2C_SECURITY_CREDENTIAL=your_encrypted_credential
MPESA_CALLBACK_URL=https://your-ngrok-url.app/api/mpesa/callback

```

4. **Initialize tables & trigger your first ETL run:**

```bash
# Registers OLTP and OLAP models to create the core tables
python main.py 

# Populates the Star Schema tables from transactional history
python etl_pipeline.py

# Verifies your analytical layout via a Pandas aggregation matrix
python query_warehouse.py

```

5. **Expose Localhost for Webhooks:**

```bash
ngrok http 8000

```

* *USSD Callback:* `https://<ngrok-url>/api/ussd`
* *M-Pesa Callback:* `https://<ngrok-url>/api/mpesa/callback`

---

## 🔮 Future Roadmap

* **AI-Powered Predictive Logistics:** Feed the historical star schema variables directly into a LightGBM model to output dynamic ETAs back into the USSD interface before a rider accepts a route.
* **Automated Agent Support:** Integrate a Retrieval-Augmented Generation (RAG) system utilizing advanced LLMs to handle tier-1 customer disputes and automated USSD/WhatsApp ticket generation.
* **E-commerce API:** Provide an open REST API allowing external platforms, Shopify setups, and Instagram business accounts to generate MzigoSafe escrow parameters automatically.

---

## 🛠️ Remaining Builds & Next Milestones

Now that the Data Warehouse is running smoothly, we have finished the foundational backend. Here is the list of builds left to take this system to a portfolio-ready or production status:

### 1. The Synthetic Data Injection Script (`generate_mock_data.py`)

* **Why it's left:** We currently only have 3 rows of data with actual timestamp numbers. We need a script that programmatically injects 500 to 1,000 highly realistic rows into our DB (matching weekend/weekday behaviors, higher delivery fees for longer pickup intervals, etc.).
* **Outcome:** Gives us an immediate, robust dataset to showcase our analytical dashboards and properly train the Machine Learning engine.

### 2. The Predictive Machine Learning Loop (`train_eta_model.py`)

* **Why it's left:** The LightGBM pipeline code is written but waiting for that data block to unlock. Once we have the data, we will run the script, tune the hyper-parameters, generate real Mean Absolute Error metrics, and save the binary model artifact (`.pkl`).

### 3. Production Model Inference Integration (`main.py` / USSD)

* **Why it's left:** Once the model is trained, we need to load it back into the FastAPI router. When a seller checks an active delivery via the USSD menu or a rider looks at a job, our LightGBM model will calculate a dynamic ETA on the fly and display: `"Est. Delivery Time: 24 Mins"`.

### 4. Interactive Live Monitoring Tool / Dashboard

* **Why it's left:** While the Pandas terminal aggregation is great, a visual dashboard (built either using lightweight Jinja2 templates or a dedicated Streamlit dashboard script) will allow an admin to visually track total escrow holdings, active disputes, and rider performance metrics.