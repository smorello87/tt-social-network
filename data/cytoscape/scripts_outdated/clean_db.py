import csv

def read_expressions_from_txt(txt_filename):
    """Read all lines from the TXT file and return them as a list of expressions."""
    with open(txt_filename, 'r') as f:
        return [line.strip() for line in f]

def remove_matched_entries_from_csv_entities_column(csv_filename, expressions):
    """Remove specific matches from the "Entities" column of the CSV file."""
    
    modified_rows = []
    
    with open(csv_filename, 'r') as f:
        reader = csv.reader(f)
        headers = next(reader)  # read the header row
        entities_index = headers.index('Entities')  # get index of the "Entities" column
        
        modified_rows.append(headers)  # add headers back to the modified rows

        for row in reader:
            entities = row[entities_index].split('; ')
            filtered_entities = [entity for entity in entities if entity not in expressions]
            row[entities_index] = '; '.join(filtered_entities)
            modified_rows.append(row)

    # Write back the modified rows to the CSV file
    with open(csv_filename, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerows(modified_rows)

if __name__ == '__main__':
    txt_filename = 'expressions.txt'
    csv_filename = 'lit.csv'

    expressions = read_expressions_from_txt(txt_filename)
    remove_matched_entries_from_csv_entities_column(csv_filename, expressions)
