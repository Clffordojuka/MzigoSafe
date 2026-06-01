# MzigoSafe

**MzigoSafe** is an offline-first, USSD-based logistics escrow platform designed to eliminate the trust deficit in the informal e-commerce sector. By leveraging a centralized virtual ledger and a strict **Dual-OTP Chain of Custody**, MzigoSafe mathematically guarantees proof-of-delivery and instant payouts, protecting sellers, buyers, and delivery riders alike.

---

## 🚀 The Problem

The informal logistics market is crippled by a lack of trust:

* **Sellers** refuse to dispatch goods without upfront payment.
* **Buyers** refuse to pay before physically inspecting the item.
* **Both parties** fear the delivery rider might disappear with the package or the cash.

Current logistics applications require smartphones, active internet connections, and complex onboarding, alienating a massive portion of the market that relies on feature phones and USSD infrastructure.

## 💡 The Solution & Core Features

MzigoSafe operates entirely over USSD (`*384*...#`) and SMS, making it accessible to 100% of mobile users with zero data requirements.

* **Virtual Escrow:** Funds are securely locked in the system before a rider is ever dispatched.
* **Dual-OTP Verification:** The system generates two unique SMS OTPs. The rider cannot progress the delivery or get paid without physically collecting the **Pickup OTP** from the seller and the **Delivery OTP** from the buyer.
* **Stateful USSD Engine:** Powered by a PostgreSQL session manager, the menus are fully crash-proof, remembering user states even if a session drops or invalid inputs are provided.
* **Reverse Logistics & Dispute Resolution:** Built-in flows allow riders to log buyer rejections at the door, automatically triggering item refunds to the buyer while securing the transit fee for the rider.
* **Real-Time Admin Dashboard:** A live web portal for logistics managers to monitor active escrow volumes, track packages in transit, and view OTP status in real-time.

---

## 🛠️ Technical Architecture

### Tech Stack

* **Backend API:** Python, FastAPI
* **Database & ORM:** PostgreSQL, SQLAlchemy
* **Frontend Dashboard:** Jinja2 Templates, Tailwind CSS
* **Telecommunications:** Africa's Talking API (USSD Gateway & SMS Messaging)

### Core System Flow

| Phase | Actor | Action | Database State |
| --- | --- | --- | --- |
| **1. Initiation** | Seller | Dials USSD, inputs Buyer number, item price, and delivery fee. | `pending_buyer_payment` |
| **2. Escrow Trap** | Buyer | Dials USSD, intercepted by Escrow Prompt, approves payment. | `funds_secured` (OTPs sent) |
| **3. Dispatch & Pickup** | Rider | Accepts job via USSD, travels to Seller, inputs **Pickup OTP**. | `in_transit` |
| **4. Handover & Payout** | Rider | Hands package to Buyer, inputs **Delivery OTP**. | `delivered` (Funds split) |
| **5. Dispute (Edge Case)** | Rider | Reports buyer rejection at drop-off. | `cancelled` (Refund issued) |

---

## ⚙️ Local Development Setup

### Prerequisites

* Python 3.8+
* PostgreSQL
* Africa's Talking Sandbox Account

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
Create a `.env` file in the root directory:
```env
DATABASE_URL=postgresql://username:password@localhost:5432/mzigosafe_db
AT_USERNAME=sandbox
AT_API_KEY=your_sandbox_api_key

```


4. **Initialize the Database:**
Run the application once to allow SQLAlchemy to create the `users`, `deliveries`, `escrow_ledger`, and `ussd_sessions` tables.
5. **Run the Application:**
```bash
uvicorn main:app --reload

```


6. **Expose to Africa's Talking:**
Use Ngrok to tunnel your local server and paste the HTTPS URL into your Africa's Talking Sandbox USSD callback settings.
```bash
ngrok http 8000

```



---

## 🔮 Future Roadmap

Moving towards a production release, the development pipeline is focused on payment integration, data warehousing, and intelligent automation.

* **Live API Integration:** Transition the internal virtual ledger to live M-Pesa STK Pushes (C2B) and B2C payouts via the Safaricom Daraja API.
* **Data Warehousing & BI:** Implement an extended star schema to extract transactional data into a dedicated warehouse, enabling comprehensive sales, route, and volume analysis via Power BI.
* **AI-Powered Predictive Logistics:** Utilize timestamp data from the stateful Dual-OTP system to train regression models (e.g., LightGBM) that forecast accurate delivery ETAs and optimize dynamic pricing based on historical route completion times.
* **Automated Agent Support:** Integrate a Retrieval-Augmented Generation (RAG) system utilizing advanced LLMs to handle tier-1 customer disputes, query routing, and automated USSD/WhatsApp support.
* **E-commerce API:** Provide an open REST API allowing external platforms, WhatsApp bots, and Instagram sellers to generate MzigoSafe escrow links automatically upon order confirmation.

---