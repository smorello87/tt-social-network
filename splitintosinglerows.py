import csv

def split_merged_entries(csv_filename):
    """Split entries in the 'Merged' column into separate rows, keeping the 'entry' value consistent."""
    
    new_rows = []
    
    with open(csv_filename, 'r') as f:
        reader = csv.reader(f)
        headers = next(reader)
        
        # Ensure the CSV has the required columns
        if 'entry' not in headers or 'Merged' not in headers:
            print("CSV file doesn't have the required 'entry' or 'Merged' columns.")
            return
        
        entry_index = headers.index('entry')
        merged_index = headers.index('Merged')
        
        new_rows.append(headers)  # add headers to the new rows list

        for row in reader:
            entry_value = row[entry_index]
            merged_values = row[merged_index].split('; ')
            for value in merged_values:
                new_rows.append([entry_value, value])

    # Write back the modified rows to the CSV file
    with open(csv_filename, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerows(new_rows)

if __name__ == '__main__':
    csv_filename = 'singlerows.csv'
    split_merged_entries(csv_filename)