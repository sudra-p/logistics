"""
Management command to seed master data for the logistics/shipping ERP.

Uses get_or_create to avoid duplicating existing records.
"""

from django.core.management.base import BaseCommand

from master_data.models import (
    Broker,
    Commodity,
    ContainerType,
    Forwarder,
    Port,
    ShippingLine,
    Transporter,
    Vessel,
)


class Command(BaseCommand):
    help = "Seed the database with comprehensive master data for logistics/shipping ERP"

    def handle(self, *args, **options):
        self.stdout.write("Seeding master data...")

        self._seed_ports()
        self._seed_shipping_lines()
        self._seed_container_types()
        self._seed_commodities()
        self._seed_forwarders()
        self._seed_transporters()
        self._seed_brokers()
        self._seed_vessels()

        self.stdout.write(self.style.SUCCESS("Master data seeding complete!"))
        self._print_summary()

    def _seed_ports(self):
        ports = [
            # India
            ("Mundra", "INMUN1", "India"),
            ("Nhava Sheva (JNPT)", "INNSA", "India"),
            ("Chennai", "INMAA", "India"),
            ("Kolkata", "INCCU", "India"),
            ("Cochin", "INCOK", "India"),
            ("Kandla", "INIXY", "India"),
            ("Tuticorin", "INTUT", "India"),
            ("Visakhapatnam", "INVTZ", "India"),
            ("Pipavav", "INPAV", "India"),
            ("Hazira", "INHZA", "India"),
            ("Mangalore", "INMLR", "India"),
            ("Paradip", "INPRT", "India"),
            ("Ennore", "INKAM", "India"),
            ("Krishnapatnam", "INKRI", "India"),
            ("Kakinada", "INKAK", "India"),
            ("Marmagoa", "INMRM", "India"),
            ("Porbandar", "INPBD", "India"),
            ("Gangavaram", "INGVN", "India"),
            ("Dhamra", "INDHA", "India"),
            ("Adani Kattupalli", "INKAT", "India"),
            ("Jamnagar", "INJAM", "India"),
            ("Mumbai", "INBOM", "India"),
            # Middle East
            ("Jebel Ali", "AEJEA", "UAE"),
            ("Abu Dhabi", "AEAUH", "UAE"),
            ("Sharjah", "AESHJ", "UAE"),
            ("Hamad Port", "QAHAM", "Qatar"),
            ("Dammam", "SADMM", "Saudi Arabia"),
            ("Jeddah", "SAJED", "Saudi Arabia"),
            ("Sohar", "OMSOH", "Oman"),
            ("Salalah", "OMSLL", "Oman"),
            ("Muscat", "OMMCT", "Oman"),
            ("Bahrain", "BHBAH", "Bahrain"),
            ("Kuwait", "KWKWI", "Kuwait"),
            # Africa
            ("Mombasa", "KEMBA", "Kenya"),
            ("Dar es Salaam", "TZDAR", "Tanzania"),
            ("Durban", "ZADUR", "South Africa"),
            ("Cape Town", "ZACPT", "South Africa"),
            ("Lagos (Apapa)", "NGLOS", "Nigeria"),
            ("Djibouti", "DJJIB", "Djibouti"),
            ("Port Sudan", "SDPZU", "Sudan"),
            ("Maputo", "MZMPM", "Mozambique"),
            ("Beira", "MZBEW", "Mozambique"),
            ("Nacala", "MZMNC", "Mozambique"),
            ("Toamasina", "MGTMM", "Madagascar"),
            # Europe
            ("Rotterdam", "NLRTM", "Netherlands"),
            ("Hamburg", "DEHAM", "Germany"),
            ("Antwerp", "BEANR", "Belgium"),
            ("Felixstowe", "GBFXT", "United Kingdom"),
            ("Southampton", "GBSOU", "United Kingdom"),
            ("Le Havre", "FRLEH", "France"),
            ("Barcelona", "ESBCN", "Spain"),
            ("Valencia", "ESVLC", "Spain"),
            ("Genoa", "ITGOA", "Italy"),
            ("Piraeus", "GRPIR", "Greece"),
            ("Algeciras", "ESALG", "Spain"),
            ("Bremerhaven", "DEBRV", "Germany"),
            ("Gdansk", "PLGDN", "Poland"),
            ("Gioia Tauro", "ITGIT", "Italy"),
            ("Marsaxlokk", "MTMAR", "Malta"),
            ("Lisbon", "PTLIS", "Portugal"),
            # Americas
            ("Long Beach", "USLGB", "USA"),
            ("Los Angeles", "USLAX", "USA"),
            ("New York/Newark", "USNYC", "USA"),
            ("Savannah", "USSAV", "USA"),
            ("Houston", "USHOU", "USA"),
            ("Miami", "USMIA", "USA"),
            ("Charleston", "USCHS", "USA"),
            ("Santos", "BRSSZ", "Brazil"),
            ("Buenos Aires", "ARBUE", "Argentina"),
            ("Callao", "PECLL", "Peru"),
            ("Cartagena", "COCTG", "Colombia"),
            ("Manzanillo", "MXZLO", "Mexico"),
            ("Colon", "PAONX", "Panama"),
            ("Vancouver", "CAVAN", "Canada"),
            ("Montreal", "CAMTR", "Canada"),
            # Asia Pacific
            ("Singapore", "SGSIN", "Singapore"),
            ("Shanghai", "CNSHA", "China"),
            ("Shenzhen", "CNSZX", "China"),
            ("Ningbo", "CNNBO", "China"),
            ("Busan", "KRPUS", "South Korea"),
            ("Hong Kong", "HKHKG", "Hong Kong"),
            ("Yokohama", "JPYOK", "Japan"),
            ("Tokyo", "JPTYO", "Japan"),
            ("Kaohsiung", "TWKHH", "Taiwan"),
            ("Tanjung Pelepas", "MYTPP", "Malaysia"),
            ("Port Klang", "MYPKG", "Malaysia"),
            ("Laem Chabang", "THLCH", "Thailand"),
            ("Ho Chi Minh City", "VNSGN", "Vietnam"),
            ("Haiphong", "VNHPH", "Vietnam"),
            ("Jakarta (Tanjung Priok)", "IDJKT", "Indonesia"),
            ("Colombo", "LKCMB", "Sri Lanka"),
            ("Chittagong", "BDCGP", "Bangladesh"),
            ("Manila", "PHMNL", "Philippines"),
            ("Xiamen", "CNXMN", "China"),
            ("Qingdao", "CNTAO", "China"),
            ("Tianjin", "CNTSN", "China"),
            ("Dalian", "CNDLC", "China"),
            ("Guangzhou", "CNGZS", "China"),
            # Additional major ports to reach 150+
            ("Tanger Med", "MAPTM", "Morocco"),
            ("Port Said", "EGPSD", "Egypt"),
            ("Alexandria", "EGALY", "Egypt"),
            ("Aqaba", "JOAQJ", "Jordan"),
            ("Haifa", "ILHFA", "Israel"),
            ("Ashdod", "ILASH", "Israel"),
            ("Bandar Abbas", "IRBND", "Iran"),
            ("Karachi", "PKKHI", "Pakistan"),
            ("Port Qasim", "PKBQM", "Pakistan"),
            ("Yangon", "MMRGN", "Myanmar"),
            ("Sihanoukville", "KHKOS", "Cambodia"),
            ("Cai Mep", "VNCMT", "Vietnam"),
            ("Surabaya", "IDSUB", "Indonesia"),
            ("Belawan", "IDBLW", "Indonesia"),
            ("Fremantle", "AUFRE", "Australia"),
            ("Melbourne", "AUMEL", "Australia"),
            ("Sydney", "AUSYD", "Australia"),
            ("Brisbane", "AUBNE", "Australia"),
            ("Auckland", "NZAKL", "New Zealand"),
            ("Tauranga", "NZTRG", "New Zealand"),
            ("Lome", "TGLFW", "Togo"),
            ("Tema", "GHTEM", "Ghana"),
            ("Abidjan", "CIABJ", "Ivory Coast"),
            ("Dakar", "SNDKR", "Senegal"),
            ("Douala", "CMDLA", "Cameroon"),
            ("Pointe Noire", "CGPNR", "Congo"),
            ("Luanda", "AOLAD", "Angola"),
            ("Port Elizabeth", "ZAPLZ", "South Africa"),
            ("Walvis Bay", "NAWVB", "Namibia"),
            ("Port Louis", "MUPLU", "Mauritius"),
            ("Norfolk", "USORF", "USA"),
            ("Seattle/Tacoma", "USSEA", "USA"),
            ("Oakland", "USOAK", "USA"),
            ("Baltimore", "USBAL", "USA"),
            ("Philadelphia", "USPHL", "USA"),
            ("New Orleans", "USMSY", "USA"),
            ("Halifax", "CAHAL", "Canada"),
            ("Prince Rupert", "CAPRR", "Canada"),
            ("Veracruz", "MXVER", "Mexico"),
            ("Lazaro Cardenas", "MXLZC", "Mexico"),
            ("San Antonio", "CLSAI", "Chile"),
            ("Valparaiso", "CLVAP", "Chile"),
            ("Guayaquil", "ECGYE", "Ecuador"),
            ("Paranagua", "BRPNG", "Brazil"),
            ("Itajai", "BRITJ", "Brazil"),
            ("Montevideo", "UYMVD", "Uruguay"),
            ("Kingston", "JMKIN", "Jamaica"),
            ("Freeport", "BSFPO", "Bahamas"),
            ("Caucedo", "DOCAU", "Dominican Republic"),
            ("Gothenburg", "SEGOT", "Sweden"),
            ("Helsinki", "FIHEL", "Finland"),
            ("St. Petersburg", "RULED", "Russia"),
            ("Constanta", "ROCND", "Romania"),
            ("Koper", "SIKOP", "Slovenia"),
            ("Rijeka", "HRRJK", "Croatia"),
            ("Trieste", "ITTRST", "Italy"),
            ("Zeebrugge", "BEZEE", "Belgium"),
            ("Dublin", "IEDUB", "Ireland"),
            ("Aarhus", "DKAAR", "Denmark"),
        ]

        created_count = 0
        for name, code, country in ports:
            _, created = Port.objects.get_or_create(
                name=name,
                defaults={"code": code, "country": country, "is_active": True},
            )
            if created:
                created_count += 1

        self.stdout.write(f"  Ports: {created_count} created, {len(ports)} total in seed")

    def _seed_shipping_lines(self):
        shipping_lines = [
            ("Maersk", "MAEU"),
            ("MSC", "MSCU"),
            ("CMA CGM", "CMDU"),
            ("COSCO", "COSU"),
            ("Hapag-Lloyd", "HLCU"),
            ("ONE (Ocean Network Express)", "ONEY"),
            ("Evergreen", "EGLV"),
            ("Yang Ming", "YMLU"),
            ("HMM", "HDMU"),
            ("ZIM", "ZIMU"),
            ("PIL (Pacific International Lines)", "PILU"),
            ("Wan Hai Lines", "WHLC"),
            ("OOCL", "OOLU"),
            ("Hamburg Sud", "SUDU"),
            ("SM Line", "SMLM"),
            ("Matson", "MATS"),
            ("IRISL", "IRIL"),
            ("Emirates Shipping Line", "ESLU"),
            ("Unifeeder", "UNAF"),
            ("X-Press Feeders", "XPRS"),
            ("Transworld Group", "TWLD"),
            ("Shreyas Shipping", "SHRE"),
            ("Sinokor Merchant Marine", "SNKO"),
        ]

        created_count = 0
        for name, code in shipping_lines:
            _, created = ShippingLine.objects.get_or_create(
                name=name,
                defaults={"code": code, "is_active": True},
            )
            if created:
                created_count += 1

        self.stdout.write(
            f"  Shipping Lines: {created_count} created, {len(shipping_lines)} total in seed"
        )

    def _seed_container_types(self):
        container_types = [
            ("20ft Standard Dry", "20GP"),
            ("40ft Standard Dry", "40GP"),
            ("40ft High Cube", "40HC"),
            ("20ft Refrigerated", "20RF"),
            ("40ft Refrigerated", "40RF"),
            ("40ft High Cube Refrigerated", "40RH"),
            ("20ft Open Top", "20OT"),
            ("40ft Open Top", "40OT"),
            ("20ft Flat Rack", "20FR"),
            ("40ft Flat Rack", "40FR"),
            ("20ft Tank", "20TK"),
            ("40ft Tank", "40TK"),
            ("45ft High Cube", "45HC"),
            ("20ft Ventilated", "20VH"),
            ("40ft Platform", "40PL"),
        ]

        created_count = 0
        for name, code in container_types:
            _, created = ContainerType.objects.get_or_create(
                name=name,
                defaults={"code": code, "is_active": True},
            )
            if created:
                created_count += 1

        self.stdout.write(
            f"  Container Types: {created_count} created, {len(container_types)} total in seed"
        )

    def _seed_commodities(self):
        commodities = [
            ("Rice", "1006"),
            ("Wheat", "1001"),
            ("Sugar", "1701"),
            ("Tea", "0902"),
            ("Coffee", "0901"),
            ("Spices", "0910"),
            ("Cotton", "5201"),
            ("Textiles", "6309"),
            ("Garments", "6109"),
            ("Pharmaceuticals", "3004"),
            ("Chemicals", "2901"),
            ("Petroleum Products", "2710"),
            ("Iron and Steel", "7206"),
            ("Auto Parts", "8708"),
            ("Electronics", "8542"),
            ("Machinery", "8479"),
            ("Plastic Products", "3926"),
            ("Rubber Products", "4016"),
            ("Ceramic Products", "6910"),
            ("Glass Products", "7013"),
            ("Furniture", "9403"),
            ("Handicrafts", "9701"),
            ("Leather Goods", "4202"),
            ("Gems and Jewellery", "7113"),
            ("Marine Products", "0306"),
            ("Processed Foods", "2106"),
            ("Fruits and Vegetables", "0810"),
            ("Granite and Marble", "6802"),
            ("Cement", "2523"),
            ("Paper Products", "4819"),
            ("Organic Chemicals", "2905"),
            ("Dyes and Pigments", "3204"),
            ("Aluminium Products", "7616"),
            ("Copper Products", "7408"),
            ("Zinc", "7901"),
            ("Manganese Ore", "2602"),
            ("Iron Ore", "2601"),
            ("Coal", "2701"),
            ("Bauxite", "2606"),
            ("Salt", "2501"),
        ]

        created_count = 0
        for name, hs_code in commodities:
            _, created = Commodity.objects.get_or_create(
                name=name,
                defaults={"hs_code": hs_code, "is_active": True},
            )
            if created:
                created_count += 1

        self.stdout.write(
            f"  Commodities: {created_count} created, {len(commodities)} total in seed"
        )

    def _seed_forwarders(self):
        forwarders = [
            ("DHL Global Forwarding", "Germany"),
            ("Kuehne + Nagel", "Switzerland"),
            ("DB Schenker", "Germany"),
            ("DSV Panalpina", "Denmark"),
            ("Expeditors", "USA"),
            ("Nippon Express", "Japan"),
            ("CEVA Logistics", "Switzerland"),
            ("Agility Logistics", "Kuwait"),
            ("Bollore Logistics", "France"),
            ("Sinotrans", "China"),
            ("UPS Supply Chain Solutions", "USA"),
            ("Hellmann Worldwide Logistics", "Germany"),
            ("Kintetsu World Express", "Japan"),
            ("C.H. Robinson", "USA"),
            ("Flexport", "USA"),
        ]

        created_count = 0
        for name, country in forwarders:
            _, created = Forwarder.objects.get_or_create(
                name=name,
                defaults={"country": country, "is_active": True},
            )
            if created:
                created_count += 1

        self.stdout.write(
            f"  Forwarders: {created_count} created, {len(forwarders)} total in seed"
        )

    def _seed_transporters(self):
        transporters = [
            "Rivigo",
            "Delhivery Freight",
            "TCI Express",
            "VRL Logistics",
            "Gati",
            "Safexpress",
            "Blue Dart Logistics",
            "Container Corporation (CONCOR)",
            "Allcargo Logistics",
            "Transport Corporation of India",
            "Mahindra Logistics",
            "TVS Supply Chain Solutions",
            "Om Logistics",
            "ABT Industries",
            "DTDC Freight",
        ]

        created_count = 0
        for name in transporters:
            _, created = Transporter.objects.get_or_create(
                name=name,
                defaults={"is_active": True},
            )
            if created:
                created_count += 1

        self.stdout.write(
            f"  Transporters: {created_count} created, {len(transporters)} total in seed"
        )

    def _seed_brokers(self):
        brokers = [
            ("CHA Services Pvt Ltd", "CHA/MUM/2019/001"),
            ("Global Customs Brokers", "CHA/DEL/2020/045"),
            ("Express Clearing House", "CHA/CHN/2018/112"),
            ("National CHA Services", "CHA/BLR/2021/078"),
            ("Premier Customs Agency", "CHA/KOL/2017/034"),
        ]

        created_count = 0
        for name, license_no in brokers:
            _, created = Broker.objects.get_or_create(
                name=name,
                defaults={"license_no": license_no, "is_active": True},
            )
            if created:
                created_count += 1

        self.stdout.write(
            f"  Brokers: {created_count} created, {len(brokers)} total in seed"
        )

    def _seed_vessels(self):
        """Seed vessels linked to their shipping lines."""
        vessels = [
            ("Maersk Mc-Kinney Moller", "9619907", "Maersk"),
            ("Maersk Eindhoven", "9632129", "Maersk"),
            ("Maersk Essen", "9632131", "Maersk"),
            ("MSC Gulsun", "9839430", "MSC"),
            ("MSC Mia", "9839442", "MSC"),
            ("MSC Isabella", "9839454", "MSC"),
            ("CMA CGM Jacques Saade", "9839194", "CMA CGM"),
            ("CMA CGM Palais Royal", "9839206", "CMA CGM"),
            ("CMA CGM Riviera", "9839218", "CMA CGM"),
            ("COSCO Shipping Universe", "9795610", "COSCO"),
            ("COSCO Shipping Galaxy", "9795622", "COSCO"),
            ("Hapag-Lloyd Afif", "9863297", "Hapag-Lloyd"),
            ("ONE Apus", "9806079", "ONE (Ocean Network Express)"),
            ("ONE Columba", "9806081", "ONE (Ocean Network Express)"),
            ("Ever Given", "9811000", "Evergreen"),
            ("Ever Ace", "9893890", "Evergreen"),
            ("YM Witness", "9684665", "Yang Ming"),
            ("YM Wellhead", "9684677", "Yang Ming"),
            ("HMM Algeciras", "9863281", "HMM"),
            ("HMM Oslo", "9863293", "HMM"),
            ("ZIM Sammy Ofer", "9930399", "ZIM"),
            ("PIL Celebes", "9347837", "PIL (Pacific International Lines)"),
            ("Wan Hai 613", "9751137", "Wan Hai Lines"),
            ("OOCL Hong Kong", "9776171", "OOCL"),
            ("Sinokor Incheon", "9315835", "Sinokor Merchant Marine"),
        ]

        created_count = 0
        for vessel_name, imo, shipping_line_name in vessels:
            try:
                shipping_line = ShippingLine.objects.get(name=shipping_line_name)
            except ShippingLine.DoesNotExist:
                shipping_line = None

            _, created = Vessel.objects.get_or_create(
                name=vessel_name,
                defaults={
                    "imo_number": imo,
                    "shipping_line": shipping_line,
                    "is_active": True,
                },
            )
            if created:
                created_count += 1

        self.stdout.write(
            f"  Vessels: {created_count} created, {len(vessels)} total in seed"
        )

    def _print_summary(self):
        self.stdout.write("\n--- Database Summary ---")
        self.stdout.write(f"  Ports: {Port.objects.count()}")
        self.stdout.write(f"  Shipping Lines: {ShippingLine.objects.count()}")
        self.stdout.write(f"  Container Types: {ContainerType.objects.count()}")
        self.stdout.write(f"  Commodities: {Commodity.objects.count()}")
        self.stdout.write(f"  Forwarders: {Forwarder.objects.count()}")
        self.stdout.write(f"  Transporters: {Transporter.objects.count()}")
        self.stdout.write(f"  Brokers: {Broker.objects.count()}")
        self.stdout.write(f"  Vessels: {Vessel.objects.count()}")
