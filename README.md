# project101: Store Management & Purchase API

Project101 is a **Django REST Framework** API for managing store inventories and complete purchase workflows, with integrated Apple Push Notifications (APNs) for order updates. It provides endpoints for product categories (sections and subsections), brands, banners, and full shopping cart operations (add/view cart, coupons, checkout with OTP). The API is built using Django 5.1.7 and Django REST Framework (DRF). It also integrates tools like DRF Nested Routers and drf-yasg for Swagger documentation, as well as third-party services (Twilio for OTP, Firebase/APNs for notifications) to deliver a complete e-commerce backend. All API responses and error messages are in Arabic by default.

---

## Table of Contents

- [Features](#features)  
- [Technologies & Frameworks](#technologies--frameworks)  
- [Installation](#installation)  
- [Usage](#usage)  
- [Project Structure](#project-structure)  
- [API Endpoints](#api-endpoints)  
- [Testing](#testing)  
- [Deployment](#deployment)  
- [Contribution Guidelines](#contribution-guidelines)  
- [License](#license)  
- [Contact](#contact)  

---

## Features

- **Category and Product Management:** Manage product categories (`Section` and `SubSection` models) and their associated products.
- **Brands and Banners:** Create and list product brands and promotional banners via CRUD API endpoints.
- **Shopping Cart & Checkout:** Endpoints to add items to a cart, view cart contents, apply coupons, and complete purchase. Checkout includes OTP verification sent via WhatsApp/SMS.
- **Coupons:** Apply discount coupons (fixed amount or percentage) and update the cart total accordingly.
- **OTP Verification:** Implements OTP (one-time password) step via Twilio for WhatsApp verification.
- **Notifications:** Push notifications to iOS (APNs) and Android (Firebase). Supports saving device tokens and sending custom notifications.
- **Swagger API Docs:** Interactive API documentation at `/swagger/`.
- **Admin Interface:** Django Admin available at `/admin/`.
- **Arabic Locale:** Default language is Arabic (`LANGUAGE_CODE='ar'`), timezone is Asia/Baghdad.

---

## Technologies & Frameworks

- **Backend:** Python 3, Django 5.1.7, Django REST Framework 3.15.2
- **Database:** SQLite (default) via `DATABASE_URL` (can switch to PostgreSQL or others).
- **API Tools:** 
  - DRF Nested Routers (`drf-nested-routers`)
  - Django Filter (`django-filter`)
  - drf-yasg for Swagger docs
- **Admin UI Enhancements:** (optional) `django-admin-interface`, `django-colorfield`
- **Messaging & Notifications:** 
  - APNs (`kalyke-apns`)
  - Firebase
  - Twilio for WhatsApp OTP
- **Utilities:** 
  - `django-cors-headers` (CORS)
  - `whitenoise` (static files)
  - `Pillow` (image processing)

---

## Installation

1. **Clone the Repository**
   ```bash
   git clone https://github.com/mortazaamer20/project101.git
   cd project101
   ```

2. **Create Virtual Environment**
   ```bash
   python -m venv venv
   source venv/bin/activate   # Windows: venv\Scripts\activate
   ```

3. **Install Dependencies**
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

4. **Set Environment Variables**

   Create a `.env` file in the project root:

   ```
   DEBUG=True
   SECRET_KEY=your-secret-key
   DATABASE_URL=sqlite:///db.sqlite3
   APNS_USE_SANDBOX=True
   APNS_TEAM_ID=YOUR_TEAM_ID
   APNS_AUTH_KEY_ID=YOUR_KEY_ID
   APNS_AUTH_KEY_PATH=/path/to/AuthKey.p8
   APNS_BUNDLE_ID=com.example.app
   TWILIO_ACCOUNT_SID=ACXXXXXXXXXXXXXXXXXXXXXXXXXXXX
   TWILIO_AUTH_TOKEN=your_twilio_token
   TWILIO_VERIFY_SERVICE_SID=VAXXXXXXXXXXXXXXXXXXXXXXXX
   TELEGRAM_BOT_TOKEN=123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11
   TELEGRAM_CHAT_ID=987654321
   CORS_ALLOWED_ORIGINS=http://localhost:3000,http://yourfrontend.com
   ```

5. **Apply Migrations**
   ```bash
   python manage.py migrate
   ```

6. **Create Superuser**
   ```bash
   python manage.py createsuperuser
   ```

7. **Run Server**
   ```bash
   python manage.py runserver
   ```

---

## Usage

- **API Prefix:** All endpoints are under `/api/`.
- **Authentication:** No authentication enforced by default (optional to add Token Auth).
- **Media Files:** Served from `/media/` during development.
- **Static Files:** Served via WhiteNoise or collected via `collectstatic`.

Example API Request:
```bash
GET http://127.0.0.1:8000/api/sections/
```

Admin Panel:
```bash
http://127.0.0.1:8000/admin/
```

Swagger API Docs:
```bash
http://127.0.0.1:8000/swagger/
```

---

## Project Structure

```
project101/
├── api/
│   ├── models.py        # Database models
│   ├── serializers.py   # DRF serializers
│   ├── views.py         # API views
│   ├── urls.py          # API URL routing
├── manage.py
├── requirements.txt
├── .env
├── README.md
└── static/
└── media/
```

---

## API Endpoints

| Method | Endpoint                             | Description |
|:-------|:--------------------------------------|:------------|
| GET    | /api/sections/                        | List all sections |
| GET    | /api/sections/{id}/subsections/        | List subsections under a section |
| GET    | /api/products/                        | List all products |
| POST   | /api/cart/add/                        | Add item to cart |
| GET    | /api/cart/view/                       | View cart |
| POST   | /api/cart/apply-coupon/                | Apply a coupon |
| POST   | /api/cart/checkout/                    | Checkout and send OTP |
| POST   | /api/cart/verify-otp-and-purchase/     | Verify OTP and complete order |
| POST   | /api/save-device-token/                | Save device token |
| POST   | /api/send-notification/                | Send push notification |

---

## Testing

Run tests using Django’s test framework:
```bash
python manage.py test
```

---

## Deployment

- Set `DEBUG=False` in `.env`
- Configure proper database (e.g., PostgreSQL)
- Set up production WSGI server (Gunicorn/Uvicorn)
- Serve static files (`collectstatic`)
- Configure APNs production certificates

---

## Contribution Guidelines

- Fork the repository.
- Create a new branch (`feature/your-feature`).
- Make your changes.
- Submit a pull request.

---

## License

This project is licensed under the MIT License.

---

## Contact

For questions, open an issue or contact the maintainer directly:

- GitHub: [mortazaamer20](https://github.com/mortazaamer20)
- Email: youremail@example.com

---
