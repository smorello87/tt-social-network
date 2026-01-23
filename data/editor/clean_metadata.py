#!/usr/bin/env python3
"""
Clean Omeka metadata - extract clean titles, standardize publishers, trim creators.
"""

import re
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "omeka_staging.db"

def clean_title(title):
    """Extract clean title, removing bibliographic suffix like 'City: Publisher, Year.'"""
    if not title:
        return title

    # Decode HTML entities
    title = title.replace('&amp;', '&').replace('&quot;', '"')

    # Common city patterns (including state abbreviations)
    cities = (
        r'New York|Chicago|Boston|Brooklyn|Philadelphia|San Francisco|Los Angeles|'
        r'Washington|Paterson|Newark|London|Paris|Bologna|Napoli|Naples|Roma|Rome|'
        r'Milano|Milan|Firenze|Florence|Torino|Turin|Genova|Palermo|Bari|Catania|'
        r'Detroit|Cleveland|Pittsburgh|Baltimore|Providence|Hoboken|Jersey City|'
        r'[A-Z][a-z]+,?\s*(?:NJ|NY|CA|PA|MA|CT|IL|OH|RI|MD)'
    )

    # Pattern 1: ". City: Publisher, Year." or ". City: Publisher,."
    pattern1 = rf'\.\s*(?:{cities}):\s*[^.]+[,.]?\s*\d*s?\.?$'
    cleaned = re.sub(pattern1, '', title, flags=re.IGNORECASE)

    # Pattern 2: ". City: Publisher" at end (no year)
    if cleaned == title:
        pattern2 = rf'\.\s*(?:{cities}):\s*.+$'
        cleaned = re.sub(pattern2, '', title, flags=re.IGNORECASE)

    # Pattern 3: Generic "Word(s): Something, digits" at end after a period
    if cleaned == title:
        pattern3 = r'\.\s*[A-Z][a-zA-Z\s&,\.]+:\s*[^:]+,?\s*\d{4}s?\.?$'
        cleaned = re.sub(pattern3, '', title)

    # Pattern 4: "Title.: Publisher" or "Title.:" (malformed)
    if '.:' in cleaned:
        cleaned = re.sub(r'\.:.*$', '', cleaned)

    # Pattern 5: Trailing publisher/year after the last sentence
    # Look for "sentence. City: text" or "sentence. Publisher, year"
    if cleaned == title:
        # Try splitting on last period and checking if remainder looks like bib info
        parts = cleaned.rsplit('. ', 1)
        if len(parts) == 2:
            remainder = parts[1]
            # If remainder has "City:" or looks like "Publisher, Year"
            if re.search(r'[A-Z][a-z]+:\s', remainder) or re.search(r',\s*\d{4}', remainder):
                cleaned = parts[0]

    # Clean up trailing punctuation
    cleaned = cleaned.strip()
    cleaned = re.sub(r'\.\s*$', '', cleaned)  # Remove trailing period
    cleaned = re.sub(r',\s*$', '', cleaned)  # Remove trailing comma
    cleaned = re.sub(r':\s*$', '', cleaned)  # Remove trailing colon

    return cleaned.strip()


def clean_publisher(publisher):
    """Remove city prefix from publisher, standardize formatting."""
    if not publisher:
        return publisher

    # Decode HTML entities
    publisher = publisher.replace('&amp;', '&').replace('&quot;', '"')

    # Remove "City: " prefix
    publisher = re.sub(r'^[A-Z][a-zA-Z\s,]+:\s*', '', publisher)

    # Remove "NJ: ", "NY: " etc.
    publisher = re.sub(r'^[A-Z]{2}:\s*', '', publisher)

    # Standardize some common variations
    replacements = {
        'Libreria dei Laboratori Industriali del Mondo': 'Libreria dei Lavoratori Industriali del Mondo',
        'Libreria Editrice dei Lavoratori Industriali del Mondo': 'Libreria dei Lavoratori Industriali del Mondo',
        'The Italian American Directory Co.': 'Italian American Directory Co.',
    }

    for old, new in replacements.items():
        if publisher == old:
            publisher = new
            break

    # Trim whitespace
    return publisher.strip()


def clean_creator(creator):
    """Clean creator field - trim whitespace, minor fixes."""
    if not creator:
        return creator

    # Trim whitespace
    creator = creator.strip()

    # Decode HTML entities
    creator = creator.replace('&amp;', '&').replace('&quot;', '"')

    return creator


def main():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    # Get all items
    rows = conn.execute("SELECT id, title, creator, publisher FROM omeka_items").fetchall()

    updates = []
    for row in rows:
        item_id = row['id']

        new_title = clean_title(row['title'])
        new_creator = clean_creator(row['creator'])
        new_publisher = clean_publisher(row['publisher'])

        # Only update if something changed
        if (new_title != row['title'] or
            new_creator != row['creator'] or
            new_publisher != row['publisher']):
            updates.append((new_title, new_creator, new_publisher, item_id))

    # Apply updates
    if updates:
        conn.executemany(
            "UPDATE omeka_items SET title = ?, creator = ?, publisher = ? WHERE id = ?",
            updates
        )
        conn.commit()
        print(f"Updated {len(updates)} items")
    else:
        print("No updates needed")

    # Show some examples
    print("\nSample cleaned titles:")
    for row in conn.execute("SELECT title FROM omeka_items LIMIT 10"):
        print(f"  {row[0][:70]}...")

    conn.close()


if __name__ == "__main__":
    main()
