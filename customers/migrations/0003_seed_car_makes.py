from django.db import migrations


CAR_MAKES = [
    'ACDelco', 'Acura', 'Alfa Romeo', 'Aston Martin', 'Audi',
    'Bentley', 'BMW', 'Buick', 'BYD',
    'Cadillac', 'Changan', 'Chery', 'Chevrolet', 'Chrysler',
    'Citroën', 'Corvette', 'Cupra',
    'Dacia', 'Daewoo', 'Daihatsu', 'Dodge', 'Dongfeng', 'DS',
    'Ferrari', 'Fiat', 'Ford',
    'Geely', 'Genesis', 'GMC', 'Great Wall',
    'Haval', 'Honda', 'Hummer', 'Hyundai',
    'Infiniti', 'Isuzu',
    'Jaguar', 'Jeep',
    'Kia',
    'Lamborghini', 'Land Rover', 'Lexus', 'Lincoln', 'Lotus', 'Lucid',
    'Maserati', 'Maxus', 'Mazda', 'McLaren', 'Mercedes-Benz',
    'MG', 'MINI', 'Mitsubishi',
    'Nissan',
    'Opel',
    'Peugeot', 'Polestar', 'Porsche', 'Proton',
    'RAM', 'Renault', 'Rolls-Royce',
    'Saab', 'SEAT', 'Škoda', 'Smart', 'Subaru', 'Suzuki',
    'Tata', 'Tesla', 'Toyota',
    'Volkswagen', 'Volvo',
    'XPeng',
    'Zeekr',
    'Other',
]


def seed_makes(apps, schema_editor):
    CarMake = apps.get_model('customers', 'CarMake')
    for name in CAR_MAKES:
        CarMake.objects.get_or_create(name=name)


def remove_makes(apps, schema_editor):
    CarMake = apps.get_model('customers', 'CarMake')
    CarMake.objects.filter(name__in=CAR_MAKES).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('customers', '0002_add_car_make_and_vehicle_fields'),
    ]

    operations = [
        migrations.RunPython(seed_makes, remove_makes),
    ]
