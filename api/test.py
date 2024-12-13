from unittest.mock import patch
from django.test import TestCase
from django.urls import reverse
from .models import Section, SubSection, Product, Cart, CartItem

class OtpFlowTests(TestCase):
    def setUp(self):
        # Create necessary hierarchical data
        self.section = Section.objects.create(name="Test Section")
        self.subsection = SubSection.objects.create(section=self.section, name="Test Subsection")

        # Create a product
        self.product = Product.objects.create(
            sub_section=self.subsection,
            title="Test Product",
            price=100,
            quantity=10
        )

        # Create a cart and add an item so it's not empty
        self.cart = Cart.objects.create()
        CartItem.objects.create(cart=self.cart, product=self.product, quantity=1)

    def test_otp_flow(self):
        # Step 1: Send OTP (Checkout)
        # Mock the Twilio verify services call for sending the OTP
        with patch('api.utility.client.verify') as mock_verify:
            mock_services = mock_verify.services
            mock_services.return_value.verifications.create.return_value.status = 'pending'
                            
            response = self.client.post(reverse('cart-checkout'), {
                'cart_id': str(self.cart.cart_id),
                'username': 'John Doe',
                'government': 'SomeGovernment',
                'address': '123 Street',
                'phone_number': '+123456789'
            })

            # Expecting a 200 OK and 'OTP sent successfully' message
            self.assertEqual(response.status_code, 200)
            self.assertIn('OTP sent successfully', response.json()['message'])

        # Step 2: Verify OTP and finalize purchase
        # Mock the Twilio verify services call for checking the OTP
        with patch('api.utility.client.verify.services') as mock_services:
            # Simulate Twilio returning 'approved' for OTP verification
            mock_services.return_value.verification_checks.create.return_value.status = 'approved'
            
            response = self.client.post(reverse('cart-verify-otp'), {
                'cart_id': str(self.cart.cart_id),
                'username': 'John Doe',
                'government': 'SomeGovernment',
                'address': '123 Street',
                'phone_number': '+123456789',
                'code': '123456'
            })

            # Expecting 201 Created and 'Order placed successfully'
            self.assertEqual(response.status_code, 201)
            self.assertIn('Order placed successfully', response.json()['message'])
