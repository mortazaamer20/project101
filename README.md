#project101: Store Management & Purchase API
Project101 is a Django REST Framework API for managing store inventories and complete purchase workflows, with integrated Apple Push Notifications (APNs) for order updates. It provides endpoints for product categories (sections and subsections), brands, banners, and full shopping cart operations (add/view cart, coupons, checkout with OTP). The API is built using Django 5.1.7 and Django REST Framework (DRF)​
github.com
​
github.com
. It also integrates tools like DRF Nested Routers and drf-yasg for Swagger documentation, as well as third-party services (Twilio for OTP, Firebase/APNs for notifications) to deliver a complete e-commerce backend. All API responses and error messages are in Arabic by default, reflecting its locale settings.
Table of Contents
Features
Technologies & Frameworks
Installation
Usage
Project Structure
API Endpoints
Testing
Deployment
Contribution Guidelines
License
Contact
Features
Category and Product Management: Manage product categories (Section and SubSection models) and their associated products. Nested API endpoints allow querying subsections of a given section​
github.com
​
github.com
.
Brands and Banners: Create and list product brands and promotional banners via CRUD API endpoints.
Shopping Cart & Checkout: Endpoints to add items to a cart, view cart contents, apply coupons, and complete purchase. The checkout process includes OTP verification (sent via WhatsApp/SMS) to finalize orders​
github.com
​
github.com
.
Coupons: Apply discount coupons to the cart. The API validates coupon codes (fixed amount or percentage) and updates the cart total​
github.com
​
github.com
.
OTP Verification: Implements an OTP (one-time password) step sent via Twilio to the customer’s WhatsApp number during checkout. The VerifyOTPAndPurchase endpoint validates the OTP and creates the order upon successful verification​
github.com
​
github.com
.
Notifications: Supports push notifications to iOS and Android devices. Clients can save device tokens (save-device-token/ endpoint) and send arbitrary notifications via the /send-notification/ endpoint, which uses APNs for iOS and Firebase for Android​
github.com
​
github.com
. After order creation, the system also notifies admins via a Telegram bot and admins receive app push notifications.
Swagger API Docs: Integrated Swagger UI at /swagger/ for interactive API exploration (provided by drf-yasg).
Admin Interface: Django’s admin panel is enabled (/admin/) for administrative tasks (inventory, orders, etc.).
Locale: Default language is Arabic (LANGUAGE_CODE='ar') and timezone is Asia/Baghdad, suitable for Arabic-speaking regions​
github.com
.
Technologies & Frameworks
Backend: Python 3, Django 5.1.7​
github.com
, Django REST Framework (DRF) 3.15.2​
github.com
.
Database: Configured via DATABASE_URL (default SQLite for development) using django-environ​
github.com
.
API Tools: DRF Nested Routers (drf-nested-routers), Django Filter (django-filter), drf-yasg for Swagger/OpenAPI docs.
Admin UI: Customizable admin interface via django-admin-interface and django-colorfield for rich admin themes (optional).
Notifications & Messaging:
APNs: Push notifications using kalyke-apns.
WhatsApp/SMS: Twilio Verify service for sending OTP via WhatsApp (requires Twilio credentials)​
github.com
.
Cloud Integrations: Google Cloud & Firebase libraries are included (for potential data storage or messaging), though primary use is for push notifications.
Other Libraries: django-cors-headers (CORS), whitenoise (static file serving), Pillow (image handling), and others as listed in requirements.txt​
github.com
​
github.com
.
Installation
Clone the repository:
git clone https://github.com/mortazaamer20/project101.git
cd project101
Set up Python environment:
Ensure you have Python 3.10+ installed. Create and activate a virtual environment:
python -m venv venv
source venv/bin/activate  # On Windows use `venv\Scripts\activate`
Install dependencies:
pip install --upgrade pip
pip install -r requirements.txt
Configure environment variables:
Copy the provided .env file and fill in the necessary values. At minimum, set:
SECRET_KEY – a Django secret key (production: use a secure random value)​
github.com
.
DEBUG – set to True for development (the repository .env uses DEBUG=True)​
github.com
.
DATABASE_URL – database connection (default uses SQLite: sqlite:///db.sqlite3​
github.com
). You can switch to PostgreSQL or others as needed.
APNS_* – your Apple Push Notification credentials (team ID, key ID, bundle ID, and the path to your .p8 key file)​
github.com
.
TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_VERIFY_SERVICE_SID – Twilio credentials for sending OTP via WhatsApp​
github.com
.
TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID – for admin Telegram notifications.
CORS_ALLOWED_ORIGINS – list of allowed frontend URLs (e.g., your frontend domain)​
github.com
.
Example (in .env):
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
Apply migrations and prepare the database:
python manage.py migrate
Create a superuser (optional):
python manage.py createsuperuser
Run the development server:
python manage.py runserver
The API will be available at http://127.0.0.1:8000/. You can access the Django admin at /admin/ and the Swagger UI at /swagger/.
Usage
API Requests: Use tools like curl or Postman to interact with the API endpoints (see API Endpoints below). All endpoints are prefixed with /api/. Example:
GET http://127.0.0.1:8000/api/sections/
Authentication: This project currently does not enforce authentication on API endpoints (all operations are public). The admin interface requires login as configured. You can add authentication (e.g., Token Auth) if needed by enabling Django REST Framework’s auth classes and creating users.
Media Files: Uploaded images (e.g., section images, product images) are served from the media/ directory by default during development (see MEDIA_URL and MEDIA_ROOT in settings​
github.com
).
Static Files: In production, collect static files (python manage.py collectstatic) and serve them via a suitable web server or CDN (WhiteNoise is included for simple static file serving).
Project Structure
project101/              # Root directory
├── api/                 # Django app containing models, views, serializers, URLs
│   ├── models.py       # Defines models (Section, SubSection, Product, Order, etc.)
│   ├── serializers.py  # DRF serializers for each model
│   ├── views.py        # API views and viewsets (implements endpoints)
│   ├── urls.py         # API routes and nested routers
│   └── ...             # Other app files (utilities, tests)
├── core/                # Django project settings
│   ├── settings.py     # Project settings (env config, installed apps)
│   ├── urls.py         # Project URL config (includes api.urls, swagger, admin)
│   ├── wsgi.py         # WSGI application entrypoint
│   └── celery.py       # (Optional) Celery configuration if using background tasks
├── media/               # Uploaded media files (sections, product images, etc.)
├── product_images/      # Sample or initial product images (if any)
├── db.sqlite3           # SQLite database (default, can be replaced)
├── .env                # Environment variables (not committed to repo in production)
├── requirements.txt     # Python dependencies
├── manage.py            # Django CLI utility
└── README.md            # <this file> Project documentation
Key directories: The api/ folder contains the core application logic (models like Customer, Order, Coupon, etc., and view classes such as SectionViewSet, CheckoutView, VerifyOTPAndPurchaseView, etc.)​
github.com
​
github.com
. The core/ folder holds project-wide settings and URL routes (including Swagger and admin)​
github.com
​
github.com
.
API Endpoints
The API base URL is /api/. Endpoints include (all return JSON):
Categories & Products:
GET /api/sections/ – List all sections.
GET /api/sections/{id}/ – Retrieve a single section (includes its subsections).
GET /api/sections/{section_id}/subsections/ – List subsections of a section (nested router).
GET /api/subsections/ – List all subsections.
GET /api/subsections/{id}/ – Retrieve a subsection (includes its products).
GET /api/products/ – List all products (supports search, filter, ordering).
GET /api/products/{id}/ – Retrieve a single product.
GET /api/brands/ – List all brands.
GET /api/brands/{id}/ – Retrieve a brand.
GET /api/banners/ – List all banners (for promotional images).
GET /api/banners/{id}/ – Retrieve a banner.
Shopping Cart & Checkout:
POST /api/cart/add/ – Add items to a cart or update quantities. Requires JSON { "cart_id": "<uuid>", "products": [ {"id": <product_id>, "quantity": <n>}, ... ] }.
GET /api/cart/view/?cart_id=<uuid> – View cart contents (sends cart_id as query param).
POST /api/cart/apply-coupon/ – Apply a coupon to the cart. Body: { "coupon_code": "<CODE>" }.
POST /api/cart/checkout/ – Begin checkout (generate OTP). Body expects customer info: { "cart_id": "<uuid>", "username": "...", "government": "...", "address": "...", "phone_number": "...", "coupon_code": "<CODE>" }. On success, sends OTP via WhatsApp/SMS​
github.com
​
github.com
.
POST /api/cart/verify-otp/ – Verify OTP and finalize purchase. Body: { "cart_id": "<uuid>", "username": "...", "government": "...", "address": "...", "phone_number": "...", "code": "<OTP>" }. If OTP matches, an Order is created and confirmation is sent.
Device & Notification:
POST /api/cart/save-device-token/ – Save/update a device push token. Body: { "token": "<device_token>", "platform": "ios"|"android" }. Registers the device for push notifications​
github.com
.
POST /api/cart/send-notification/ – Send a test notification to a device. Body: { "token": "<device_token>", "platform": "ios"|"android", "title": "...", "message": "..." }. Uses APNs for iOS or FCM for Android to push the message​
github.com
.
Swagger documentation is available at GET /swagger/ (use the web UI to explore all endpoints and payload schemas).
Testing
This repository does not include automated test suites (the api/tests.py is currently empty)​
github.com
. To test functionality, interact with the API endpoints manually using tools like Postman, curl, or via the Swagger UI. You can also write your own Django tests within the api/ app and run them with python manage.py test.
Deployment
Production Setup: For production deployment, set DEBUG=False and configure ALLOWED_HOSTS in your environment. Use a robust database (e.g., PostgreSQL) by setting DATABASE_URL.
Static Files: Run python manage.py collectstatic to gather static assets. Use a production-ready web server (e.g., Gunicorn or uWSGI behind Nginx). WhiteNoise is already included to serve static files if a dedicated static server is not used.
Environment Variables: Ensure all required secrets (SECRET_KEY, Twilio, APNs, Telegram tokens, etc.) are set securely in the environment or in a production .env file.
HTTPS: Configure HTTPS (TLS/SSL) in front-end or API gateway if exposing API endpoints publicly.
Scaling: The app can be containerized (e.g., Docker) by using the same steps (install deps, run migrations, start Gunicorn). Consider adding a superviser for Celery if using background tasks (Celery config is included).
Contribution Guidelines
Contributions are welcome! To contribute:
Fork the repository on GitHub and create a feature branch.
Implement your changes (follow PEP 8 style, include tests if applicable).
Commit your work with clear commit messages.
Open a Pull Request against the main branch describing your changes.
Discussion and review: Await feedback and revise as needed.
For bug reports or feature requests, please use the GitHub Issues page. Note: This project currently does not have a formal LICENSE file. If you plan to use or distribute this code, clarify licensing with the maintainers or consider adding a license.
License
No license file was found in this repository. This means the code is not explicitly licensed for open use. Use or distribute the code at your own risk, or contact the project maintainers to request permission or licensing details.
Contact
Project contributors can be found on GitHub:
mortazaamer20 (Mora) – main author​
github.com
mohammed0abbas (Mohammed) – contributor​
github.com
For questions or support, please raise an issue on the GitHub repository.
