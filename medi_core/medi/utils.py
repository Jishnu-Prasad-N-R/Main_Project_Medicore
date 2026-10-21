from twilio.rest import Client
from decouple import config
import logging

logger = logging.getLogger(__name__)

class SMSNotificationService:
    def __init__(self):
        """
        Initialize Twilio Client and load the Developer Number for the demo.
        """
        try:
            self.client = Client(config('TWILIO_ACCOUNT_SID'), config('TWILIO_AUTH_TOKEN'))
            self.from_number = config('TWILIO_SENDER')
            self.developer_number = config('MY_NUMBER')
        except Exception as e:
            logger.error(f"Twilio Configuration Error: {e}")
            self.client = None

    def send_booking_confirmation(self, appointment):
        """
        Sends a booking confirmation SMS.
        REDIRECTS all messages to the Developer Number for testing/demo purposes.
        """
        if not self.client:
            logger.error("Twilio Client not initialized. Check your .env file.")
            return False

        try:
        
            patient_name = f"{appointment.patient.user.first_name} {appointment.patient.user.last_name}" 
            doctor_name = f"{appointment.doctor.user.first_name} {appointment.doctor.user.last_name}" 
            date = appointment.date.strftime('%b %d, %Y')
            time = appointment.time
            
            original_patient_number = appointment.patient.phone_number

            #Construct the message
            message_body = (
                f"Hi {patient_name}, Dr. {doctor_name} confirmed your appointment on {date} at {time.strftime('%I:%M %p')}. See you then! (Intended for: {original_patient_number})"
            )

            #Send the message -> FORCE IT TO GO TO YOU (Developer Number)
            message = self.client.messages.create(
                body=message_body,
                from_=self.from_number,
                to=self.developer_number 
            )
            
            logger.info(f"SMS Successfully Redirected to Developer! SID: {message.sid}")
            return True

        except Exception as e:
            logger.exception(f"Failed to send SMS: {e}")
            return False