"""Default server now serves the BankKYC frontend contract."""
from kyc.config import Settings
from kyc.main import create_app
app = create_app(Settings.from_env())
