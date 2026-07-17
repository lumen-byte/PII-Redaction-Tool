
TEST_CASES = [
    (
        "Please reach out to Rashi Patil at rashi.patil@gmail.com or call "
        "Rohan Dey on +91 9876543210 regarding the account.",
        [
            ("Rashi Patil", "PERSON"),
            ("rashi.patil@gmail.com", "EMAIL"),
            ("Rohan Dey", "PERSON"),
            ("+91 9876543210", "PHONE"),
        ],
    ),
    (
        "The Managing Director, RAJESH KUSHAL HEGDE, signed the agreement "
        "alongside Ms. Priya Sharma, Company Secretary.",
        [
            ("RAJESH KUSHAL HEGDE", "PERSON"),
            ("Priya Sharma", "PERSON"),
        ],
    ),
    (
        "The shipment was dispatched by Global Freight Solutions Private "
        "Limited and received at Acme Manufacturing Corp on the same day.",
        [
            ("Global Freight Solutions Private Limited", "ORG"),
            ("Acme Manufacturing Corp", "ORG"),
        ],
    ),
    (
        "For queries, write to support.desk@examplecorp.co.in or "
        "j.smith+billing@sub.domain.org.",
        [
            ("support.desk@examplecorp.co.in", "EMAIL"),
            ("j.smith+billing@sub.domain.org", "EMAIL"),
        ],
    ),
    (
        "You can contact the helpdesk at +91-22-4009-4400 or, for the US "
        "office, at (415) 555-0198.",
        [
            ("+91-22-4009-4400", "PHONE"),
            ("(415) 555-0198", "PHONE"),
        ],
    ),
    (
        "Our registered office is located at 11/3, Village Birdewadi, "
        "Chakan Taluka, Pune - 410501, Maharashtra, India.",
        [
            ("Village Birdewadi, Chakan Taluka, Pune - 410501", "ADDRESS"),
        ],
    ),
    (
        "Please ship the replacement unit to 742 Evergreen Terrace Street, "
        "Springfield, IL 62704 before Friday.",
        [
            ("742 Evergreen Terrace Street, Springfield, IL 62704", "ADDRESS"),
        ],
    ),
    (
        "The applicant's Social Security Number on file is 219-09-9999 for "
        "verification purposes.",
        [
            ("219-09-9999", "SSN"),
        ],
    ),
    (
        "Payment was charged to card number 4111 1111 1111 1111, and a "
        "second attempt used 5500 0055 5555 5559.",
        [
            ("4111 1111 1111 1111", "CREDIT_CARD"),
            ("5500 0055 5555 5559", "CREDIT_CARD"),
        ],
    ),
    (
        "The candidate's date of birth is March 3, 1988, as recorded on "
        "the application form.",
        [
            ("March 3, 1988", "DOB"),
        ],
    ),
    (
        "Employee record: DOB: 12/04/1990, department: Finance.",
        [
            ("12/04/1990", "DOB"),
        ],
    ),
    (
        "The suspicious login originated from IP address 203.0.113.42 at "
        "02:14 AM server time.",
        [
            ("203.0.113.42", "IP_ADDRESS"),
        ],
    ),
    (
        "Your Order #482910 has shipped. Please reference Ticket ID "
        "TCK-118820 in any follow-up correspondence.",
        [],
    ),
    (
        "Corporate Identity Number: U28129PN1979PLC141032. "
        "ISIN: INE181B01013.",
        [],
    ),
    (
        "The Offer is being made in accordance with SEBI ICDR Regulations "
        "and will be listed on BSE and NSE.",
        [],
    ),
    (
        "The company was originally incorporated on July 30, 1979, under "
        "the Companies Act, 1956.",
        [],
    ),
    (
        "The internal tracking reference for this shipment is "
        "1234567890123456.",
        [],
    ),
    (
        "The batch yield improved by 400501 units compared to last "
        "quarter.",
        [],
    ),
]
