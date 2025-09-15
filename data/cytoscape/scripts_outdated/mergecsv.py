import csv

def merge_people_and_entities_columns(csv_filename):
    """Merge the 'People' and 'Entities' columns and save the result in the 'Merged' column."""
    
    modified_rows = []
    
    with open(csv_filename, 'r') as f:
        reader = csv.reader(f)
        headers = next(reader)  # read the header row
        
        # Ensure the CSV has the required columns
        if 'People' not in headers or 'Entities' not in headers:
            print("CSV file doesn't have the required 'People' or 'Entities' columns.")
            return
        
        people_index = headers.index('People')
        entities_index = headers.index('Entities')
        
        # Add the new 'Merged' column to the headers
        headers.append('Merged')
        modified_rows.append(headers)

        for row in reader:
            merged_value = row[people_index] + '; ' + row[entities_index]
            row.append(merged_value)
            modified_rows.append(row)

    # Write back the modified rows to the CSV file
    with open(csv_filename, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerows(modified_rows)

if __name__ == '__main__':
    csv_filename = 'lit_merged.csv'
    merge_people_and_entities_columns(csv_filename)
