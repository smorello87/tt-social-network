import csv

def remove_duplicates_from_entry(csv_filename):
    """Remove duplicate rows based on the 'entry' column."""
    
    new_rows = []
    seen_entries = set()
    
    with open(csv_filename, 'r') as f:
        reader = csv.reader(f)
        headers = next(reader)  # read the header row
        
        # Ensure the CSV has the required 'entry' column
        if 'entry' not in headers:
            print("CSV file doesn't have the required 'entry' column.")
            return
        
        entry_index = headers.index('entry')
        
        new_rows.append(headers)  # add headers to the new rows list

        for row in reader:
            entry_value = row[entry_index]
            if entry_value not in seen_entries:
                new_rows.append(row)
                seen_entries.add(entry_value)

    # Write back the modified rows to the CSV file
    with open(csv_filename, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerows(new_rows)

if __name__ == '__main__':
    csv_filename = 'type1.csv'
    remove_duplicates_from_entry(csv_filename)
