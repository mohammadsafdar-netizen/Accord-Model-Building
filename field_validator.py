#!/usr/bin/env python3
"""
Field Validator: Cross-field validation and correction
========================================================
Validates extracted field values against domain rules and
cross-field consistency checks for ACORD forms.

Rules:
  1. State <-> ZIP prefix consistency
  2. Date ordering: effective_date < expiration_date
  3. Vehicle year: 1900 <= year <= current_year + 1
  4. Driver DOB: age >= 15
  5. VIN checksum (position 9 check digit)
  6. Phone number format validation (10 digits)
  7. NAIC code: exactly 5 digits

Usage:
    from field_validator import validate_and_fix
    corrected, warnings = validate_and_fix(extracted, "125", schema)
"""

from __future__ import annotations

import re
from datetime import datetime, date
from typing import Any, Dict, List, Optional, Tuple

# State -> ZIP prefix mapping (first 3 digits)
STATE_ZIP_PREFIXES = {
    "AL": ["350", "351", "352", "353", "354", "355", "356", "357", "358", "359", "360", "361", "362", "363", "364", "365", "366"],
    "AK": ["995", "996", "997", "998", "999"],
    "AZ": ["850", "851", "852", "853", "855", "856", "857", "859", "860", "863", "864", "865"],
    "AR": ["716", "717", "718", "719", "720", "721", "722", "723", "724", "725", "726", "727", "728", "729"],
    "CA": ["900", "901", "902", "903", "904", "905", "906", "907", "908", "910", "911", "912", "913", "914", "915", "916", "917", "918", "919", "920", "921", "922", "923", "924", "925", "926", "927", "928", "930", "931", "932", "933", "934", "935", "936", "937", "938", "939", "940", "941", "942", "943", "944", "945", "946", "947", "948", "949", "950", "951", "952", "953", "954", "955", "956", "957", "958", "959", "960", "961"],
    "CO": ["800", "801", "802", "803", "804", "805", "806", "807", "808", "809", "810", "811", "812", "813", "814", "815", "816"],
    "CT": ["060", "061", "062", "063", "064", "065", "066", "067", "068", "069"],
    "DE": ["197", "198", "199"],
    "DC": ["200", "202", "203", "204", "205"],
    "FL": ["320", "321", "322", "323", "324", "325", "326", "327", "328", "329", "330", "331", "332", "333", "334", "335", "336", "337", "338", "339", "340", "341", "342", "344", "346", "347", "349"],
    "GA": ["300", "301", "302", "303", "304", "305", "306", "307", "308", "309", "310", "311", "312", "313", "314", "315", "316", "317", "318", "319"],
    "HI": ["967", "968"],
    "ID": ["832", "833", "834", "835", "836", "837", "838"],
    "IL": ["600", "601", "602", "603", "604", "605", "606", "607", "608", "609", "610", "611", "612", "613", "614", "615", "616", "617", "618", "619", "620", "622", "623", "624", "625", "626", "627", "628", "629"],
    "IN": ["460", "461", "462", "463", "464", "465", "466", "467", "468", "469", "470", "471", "472", "473", "474", "475", "476", "477", "478", "479"],
    "IA": ["500", "501", "502", "503", "504", "505", "506", "507", "508", "509", "510", "511", "512", "513", "514", "515", "516", "520", "521", "522", "523", "524", "525", "526", "527", "528"],
    "KS": ["660", "661", "662", "664", "665", "666", "667", "668", "669", "670", "671", "672", "673", "674", "675", "676", "677", "678", "679"],
    "KY": ["400", "401", "402", "403", "404", "405", "406", "407", "408", "409", "410", "411", "412", "413", "414", "415", "416", "417", "418"],
    "LA": ["700", "701", "703", "704", "705", "706", "707", "708", "710", "711", "712", "713", "714"],
    "ME": ["039", "040", "041", "042", "043", "044", "045", "046", "047", "048", "049"],
    "MD": ["206", "207", "208", "209", "210", "211", "212", "214", "215", "216", "217", "218", "219"],
    "MA": ["010", "011", "012", "013", "014", "015", "016", "017", "018", "019", "020", "021", "022", "023", "024", "025", "026", "027"],
    "MI": ["480", "481", "482", "483", "484", "485", "486", "487", "488", "489", "490", "491", "492", "493", "494", "495", "496", "497", "498", "499"],
    "MN": ["550", "551", "553", "554", "555", "556", "557", "558", "559", "560", "561", "562", "563", "564", "565", "566", "567"],
    "MS": ["386", "387", "388", "389", "390", "391", "392", "393", "394", "395", "396", "397"],
    "MO": ["630", "631", "633", "634", "635", "636", "637", "638", "639", "640", "641", "644", "645", "646", "647", "648", "649", "650", "651", "652", "653", "654", "655", "656", "657", "658"],
    "MT": ["590", "591", "592", "593", "594", "595", "596", "597", "598", "599"],
    "NE": ["680", "681", "683", "684", "685", "686", "687", "688", "689", "690", "691", "692", "693"],
    "NV": ["889", "890", "891", "893", "894", "895", "897", "898"],
    "NH": ["030", "031", "032", "033", "034", "035", "036", "037", "038"],
    "NJ": ["070", "071", "072", "073", "074", "075", "076", "077", "078", "079", "080", "081", "082", "083", "084", "085", "086", "087", "088", "089"],
    "NM": ["870", "871", "873", "874", "875", "877", "878", "879", "880", "881", "882", "883", "884"],
    "NY": ["005", "100", "101", "102", "103", "104", "105", "106", "107", "108", "109", "110", "111", "112", "113", "114", "115", "116", "117", "118", "119", "120", "121", "122", "123", "124", "125", "126", "127", "128", "129", "130", "131", "132", "133", "134", "135", "136", "137", "138", "139", "140", "141", "142", "143", "144", "145", "146", "147", "148", "149"],
    "NC": ["270", "271", "272", "273", "274", "275", "276", "277", "278", "279", "280", "281", "282", "283", "284", "285", "286", "287", "288", "289"],
    "ND": ["580", "581", "582", "583", "584", "585", "586", "587", "588"],
    "OH": ["430", "431", "432", "433", "434", "435", "436", "437", "438", "439", "440", "441", "442", "443", "444", "445", "446", "447", "448", "449", "450", "451", "452", "453", "454", "455", "456", "457", "458"],
    "OK": ["730", "731", "734", "735", "736", "737", "738", "739", "740", "741", "743", "744", "745", "746", "747", "748", "749"],
    "OR": ["970", "971", "972", "973", "974", "975", "976", "977", "978", "979"],
    "PA": ["150", "151", "152", "153", "154", "155", "156", "157", "158", "159", "160", "161", "162", "163", "164", "165", "166", "167", "168", "169", "170", "171", "172", "173", "174", "175", "176", "177", "178", "179", "180", "181", "182", "183", "184", "185", "186", "187", "188", "189", "190", "191", "192", "193", "194", "195", "196"],
    "RI": ["028", "029"],
    "SC": ["290", "291", "292", "293", "294", "295", "296", "297", "298", "299"],
    "SD": ["570", "571", "572", "573", "574", "575", "576", "577"],
    "TN": ["370", "371", "372", "373", "374", "375", "376", "377", "378", "379", "380", "381", "382", "383", "384", "385"],
    "TX": ["733", "750", "751", "752", "753", "754", "755", "756", "757", "758", "759", "760", "761", "762", "763", "764", "765", "766", "767", "768", "769", "770", "771", "772", "773", "774", "775", "776", "777", "778", "779", "780", "781", "782", "783", "784", "785", "786", "787", "788", "789", "790", "791", "792", "793", "794", "795", "796", "797", "798", "799"],
    "UT": ["840", "841", "842", "843", "844", "845", "846", "847"],
    "VT": ["050", "051", "052", "053", "054", "056", "057", "058", "059"],
    "VA": ["201", "220", "221", "222", "223", "224", "225", "226", "227", "228", "229", "230", "231", "232", "233", "234", "235", "236", "237", "238", "239", "240", "241", "242", "243", "244", "245", "246"],
    "WA": ["980", "981", "982", "983", "984", "985", "986", "988", "989", "990", "991", "992", "993", "994"],
    "WV": ["247", "248", "249", "250", "251", "252", "253", "254", "255", "256", "257", "258", "259", "260", "261", "262", "263", "264", "265", "266", "267", "268"],
    "WI": ["530", "531", "532", "534", "535", "537", "538", "539", "540", "541", "542", "543", "544", "545", "546", "547", "548", "549"],
    "WY": ["820", "821", "822", "823", "824", "825", "826", "827", "828", "829", "830", "831"],
}


def _parse_date(value: str) -> Optional[date]:
    """Try to parse a date string in common formats."""
    if not value or not isinstance(value, str):
        return None
    value = value.strip()
    for fmt in ("%m/%d/%Y", "%m-%d-%Y", "%Y-%m-%d", "%m/%d/%y", "%m-%d-%y"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None


def _extract_digits(value: str) -> str:
    """Extract only digits from a string."""
    return re.sub(r"[^\d]", "", str(value))


def _validate_vin_checksum(vin: str) -> bool:
    """Validate VIN check digit (position 9). Returns True if valid or cannot verify."""
    vin = vin.strip().upper()
    if len(vin) != 17:
        return True  # Can't validate non-17 char VINs

    transliteration = {
        'A': 1, 'B': 2, 'C': 3, 'D': 4, 'E': 5, 'F': 6, 'G': 7, 'H': 8,
        'J': 1, 'K': 2, 'L': 3, 'M': 4, 'N': 5, 'P': 7, 'R': 9,
        'S': 2, 'T': 3, 'U': 4, 'V': 5, 'W': 6, 'X': 7, 'Y': 8, 'Z': 9,
    }
    weights = [8, 7, 6, 5, 4, 3, 2, 10, 0, 9, 8, 7, 6, 5, 4, 3, 2]

    total = 0
    for i, char in enumerate(vin):
        if char.isdigit():
            val = int(char)
        elif char in transliteration:
            val = transliteration[char]
        else:
            return True  # Invalid char, can't verify
        total += val * weights[i]

    remainder = total % 11
    check_digit = 'X' if remainder == 10 else str(remainder)
    return vin[8] == check_digit


def validate_and_fix(
    extracted: Dict[str, Any],
    form_type: str,
    schema: Any = None,
) -> Tuple[Dict[str, Any], List[str]]:
    """Run cross-field validation rules. Returns (corrected_fields, warnings).

    Only warns; does not remove values (OCR might be right even if validation flags it).
    """
    corrected = dict(extracted)
    warnings: List[str] = []
    current_year = datetime.now().year

    # Collect state and ZIP fields for cross-check
    state_zip_pairs: List[Tuple[str, str]] = []
    for key in corrected:
        key_lower = key.lower()
        if "state" in key_lower and "zip" not in key_lower:
            # Find matching ZIP field (same prefix/suffix pattern)
            prefix = key.rsplit("State", 1)[0] if "State" in key else key.rsplit("state", 1)[0]
            for zip_key in corrected:
                if zip_key.lower().startswith(prefix.lower()) and "zip" in zip_key.lower():
                    state_zip_pairs.append((key, zip_key))
                    break

    # Rule 1: State <-> ZIP prefix consistency
    for state_key, zip_key in state_zip_pairs:
        state_val = str(corrected.get(state_key, "")).strip().upper()
        zip_val = str(corrected.get(zip_key, "")).strip()
        zip_digits = _extract_digits(zip_val)

        if state_val and zip_digits and len(zip_digits) >= 3:
            zip_prefix = zip_digits[:3]
            valid_prefixes = STATE_ZIP_PREFIXES.get(state_val, [])
            if valid_prefixes and zip_prefix not in valid_prefixes:
                warnings.append(
                    f"State/ZIP mismatch: {state_key}={state_val} but {zip_key}={zip_val} "
                    f"(prefix {zip_prefix} not valid for {state_val})"
                )

    # Rule 2: Date ordering (effective < expiration)
    eff_keys = [k for k in corrected if re.search(r"effective.*date|date.*effective|eff.*date", k, re.I)]
    exp_keys = [k for k in corrected if re.search(r"expiration.*date|date.*expir|exp.*date", k, re.I)]

    for eff_key in eff_keys:
        eff_date = _parse_date(str(corrected.get(eff_key, "")))
        if not eff_date:
            continue
        for exp_key in exp_keys:
            # Match by prefix/suffix pattern
            exp_date = _parse_date(str(corrected.get(exp_key, "")))
            if exp_date and eff_date >= exp_date:
                warnings.append(
                    f"Date ordering: {eff_key}={corrected[eff_key]} should be before "
                    f"{exp_key}={corrected[exp_key]}"
                )

    # Rule 3: Vehicle year validation
    for key in corrected:
        if re.search(r"vehicle.*year|year.*model|modelyear", key, re.I):
            year_val = _extract_digits(str(corrected[key]))
            if year_val and len(year_val) == 4:
                year_int = int(year_val)
                if year_int < 1900 or year_int > current_year + 1:
                    warnings.append(
                        f"Vehicle year out of range: {key}={corrected[key]} "
                        f"(expected 1900-{current_year + 1})"
                    )

    # Rule 4: Driver DOB (age >= 15)
    for key in corrected:
        if re.search(r"driver.*dob|driver.*birth|dob.*driver|dateofbirth", key, re.I):
            dob = _parse_date(str(corrected[key]))
            if dob:
                age = (date.today() - dob).days / 365.25
                if age < 15:
                    warnings.append(
                        f"Driver too young: {key}={corrected[key]} (age {age:.0f} < 15)"
                    )
                elif age > 120:
                    warnings.append(
                        f"Driver age implausible: {key}={corrected[key]} (age {age:.0f} > 120)"
                    )

    # Rule 5: VIN checksum
    for key in corrected:
        if re.search(r"vin|vehicle.*ident", key, re.I):
            vin_val = str(corrected[key]).strip()
            if len(vin_val) == 17 and not _validate_vin_checksum(vin_val):
                warnings.append(f"VIN check digit invalid: {key}={vin_val}")

    # Rule 6: Phone number format (should be 10 digits)
    for key in corrected:
        if re.search(r"phone|fax|telephone|tel\b", key, re.I):
            phone_val = str(corrected[key]).strip()
            digits = _extract_digits(phone_val)
            if digits and len(digits) not in (0, 10, 11):
                warnings.append(
                    f"Phone number format: {key}={phone_val} "
                    f"({len(digits)} digits, expected 10)"
                )

    # Rule 7: NAIC code (exactly 5 digits)
    for key in corrected:
        if re.search(r"naic", key, re.I):
            naic_val = str(corrected[key]).strip()
            digits = _extract_digits(naic_val)
            if digits and len(digits) != 5:
                warnings.append(
                    f"NAIC code format: {key}={naic_val} "
                    f"({len(digits)} digits, expected 5)"
                )

    return corrected, warnings
