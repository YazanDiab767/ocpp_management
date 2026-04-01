from decimal import Decimal

from django.conf import settings
from django.db import models


class Customer(models.Model):

    class VehicleType(models.TextChoices):
        ACDELCO = 'acdelco', 'ACDelco'
        ACURA = 'acura', 'Acura'
        ALFA_ROMEO = 'alfa-romeo', 'Alfa Romeo'
        ASTON_MARTIN = 'aston-martin', 'Aston Martin'
        AUDI = 'audi', 'Audi'
        BENTLEY = 'bentley', 'Bentley'
        BMW = 'bmw', 'BMW'
        BUICK = 'buick', 'Buick'
        BYD = 'byd', 'BYD'
        CADILLAC = 'cadillac', 'Cadillac'
        CHANGAN = 'changan', 'Changan'
        CHERY = 'chery', 'Chery'
        CHEVROLET = 'chevrolet', 'Chevrolet'
        CHRYSLER = 'chrysler', 'Chrysler'
        CITROEN = 'citroen', 'Citroën'
        CORVETTE = 'corvette', 'Corvette'
        CUPRA = 'cupra', 'Cupra'
        DACIA = 'dacia', 'Dacia'
        DAEWOO = 'daewoo', 'Daewoo'
        DAIHATSU = 'daihatsu', 'Daihatsu'
        DODGE = 'dodge', 'Dodge'
        DONGFENG = 'dongfeng', 'Dongfeng'
        DS = 'ds', 'DS'
        FERRARI = 'ferrari', 'Ferrari'
        FIAT = 'fiat', 'Fiat'
        FORD = 'ford', 'Ford'
        GEELY = 'geely', 'Geely'
        GENESIS = 'genesis', 'Genesis'
        GMC = 'gmc', 'GMC'
        GREAT_WALL = 'great-wall', 'Great Wall'
        HAVAL = 'haval', 'Haval'
        HONDA = 'honda', 'Honda'
        HUMMER = 'hummer', 'Hummer'
        HYUNDAI = 'hyundai', 'Hyundai'
        INFINITI = 'infiniti', 'Infiniti'
        ISUZU = 'isuzu', 'Isuzu'
        JAGUAR = 'jaguar', 'Jaguar'
        JEEP = 'jeep', 'Jeep'
        KIA = 'kia', 'Kia'
        LAMBORGHINI = 'lamborghini', 'Lamborghini'
        LAND_ROVER = 'land-rover', 'Land Rover'
        LEXUS = 'lexus', 'Lexus'
        LINCOLN = 'lincoln', 'Lincoln'
        LOTUS = 'lotus', 'Lotus'
        LUCID = 'lucid', 'Lucid'
        MASERATI = 'maserati', 'Maserati'
        MAXUS = 'maxus', 'Maxus'
        MAZDA = 'mazda', 'Mazda'
        MCLAREN = 'mclaren', 'McLaren'
        MERCEDES_BENZ = 'mercedes-benz', 'Mercedes-Benz'
        MG = 'mg', 'MG'
        MINI = 'mini', 'MINI'
        MITSUBISHI = 'mitsubishi', 'Mitsubishi'
        NISSAN = 'nissan', 'Nissan'
        OPEL = 'opel', 'Opel'
        PEUGEOT = 'peugeot', 'Peugeot'
        POLESTAR = 'polestar', 'Polestar'
        PORSCHE = 'porsche', 'Porsche'
        PROTON = 'proton', 'Proton'
        RAM = 'ram', 'RAM'
        RENAULT = 'renault', 'Renault'
        ROLLS_ROYCE = 'rolls-royce', 'Rolls-Royce'
        SAAB = 'saab', 'Saab'
        SEAT = 'seat', 'SEAT'
        SKODA = 'skoda', 'Škoda'
        SMART = 'smart', 'Smart'
        SUBARU = 'subaru', 'Subaru'
        SUZUKI = 'suzuki', 'Suzuki'
        TATA = 'tata', 'Tata'
        TESLA = 'tesla', 'Tesla'
        TOYOTA = 'toyota', 'Toyota'
        VOLKSWAGEN = 'volkswagen', 'Volkswagen'
        VOLVO = 'volvo', 'Volvo'
        XPENG = 'xpeng', 'XPeng'
        ZEEKR = 'zeekr', 'Zeekr'
        OTHER = 'other', 'Other'

    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    phone_number = models.CharField(max_length=20, unique=True, db_index=True)
    email = models.EmailField(blank=True, default='')
    id_number = models.CharField(
        max_length=20, blank=True, default='',
        help_text='National ID or passport number',
    )
    vehicle_plate = models.CharField(max_length=20, blank=True, default='')
    vehicle_type = models.CharField(
        max_length=20, choices=VehicleType.choices, blank=True, default='',
    )
    vehicle_model = models.CharField(max_length=100, blank=True, default='')
    vehicle_year = models.PositiveIntegerField(null=True, blank=True)
    notes = models.TextField(blank=True, default='')
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_customers',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'customers_customer'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['last_name', 'first_name']),
        ]

    def __str__(self):
        return f'{self.first_name} {self.last_name}'

    @property
    def full_name(self):
        return f'{self.first_name} {self.last_name}'


class Wallet(models.Model):

    customer = models.OneToOneField(
        Customer,
        on_delete=models.CASCADE,
        related_name='wallet',
    )
    balance = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'customers_wallet'

    def __str__(self):
        return f'Wallet({self.customer}) = {self.balance} ILS'


class WalletTransaction(models.Model):

    class TransactionType(models.TextChoices):
        TOPUP = 'topup', 'Top Up (Cash)'
        CHARGE_DEDUCTION = 'charge_deduction', 'Charging Deduction'
        ADJUSTMENT = 'adjustment', 'Manual Adjustment'
        REFUND = 'refund', 'Refund'

    wallet = models.ForeignKey(
        Wallet,
        on_delete=models.CASCADE,
        related_name='transactions',
    )
    transaction_type = models.CharField(
        max_length=20,
        choices=TransactionType.choices,
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    balance_before = models.DecimalField(max_digits=10, decimal_places=2)
    balance_after = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.CharField(max_length=255, blank=True, default='')
    reference_type = models.CharField(
        max_length=50, blank=True, default='',
        help_text='E.g. charging_session, manual',
    )
    reference_id = models.CharField(
        max_length=50, blank=True, default='',
        help_text='E.g. session ID or receipt number',
    )
    receipt_number = models.CharField(max_length=50, blank=True, default='')
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='wallet_transactions',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'customers_wallet_transaction'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['wallet', '-created_at']),
            models.Index(fields=['transaction_type']),
            models.Index(fields=['reference_type', 'reference_id']),
        ]

    def __str__(self):
        return f'{self.get_transaction_type_display()}: {self.amount} ILS'
