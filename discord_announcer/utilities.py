from corptools.models import EveLocation, EveItemType

import math

millnames = ['',' Thousand',' Million',' Billion',' Trillion']

def millify(n):
    n = float(n)
    millidx = max(0,min(len(millnames)-1,
                        int(math.floor(0 if n == 0 else math.log10(abs(n))/3))))

    return '{:.0f}{}'.format(n / 10**(3 * millidx), millnames[millidx])

def format_sales(sales) -> list:
    # get all location IDs
    locations = set(sale['location_id'] for sale in sales) 
    location_dict = {loc.location_id: loc.location_name for loc in EveLocation.objects.filter(location_id__in=locations)}

    type_ids = set(sale['type_id'] for sale in sales)
    type_dict = {t['type_id']: t['name'] for t in EveItemType.objects.filter(type_id__in=type_ids).values('type_id', 'name').order_by('name')}

    # header = location id
    # message = rest
    formatted_sales = []
    for loc_id in location_dict.keys():
        formatted_sale = []

        for type_id in type_dict.keys():
            # sales for type id and location id
            sale = [s for s in sales if s['location_id'] == loc_id and s['type_id'] == type_id]
            sum_unit_price = sum(s['unit_price'] for s in sale)
            sum_quantity = sum(s['quantity'] for s in sale)
            formatted_sale.append(f"{type_dict[type_id]} x {sum_quantity} for {millify(sum_unit_price)} Isk" )
        formatted_sales.append( (location_dict[loc_id], "\n".join(formatted_sale)) )

    return formatted_sales