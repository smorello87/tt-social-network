import csv
from collections import defaultdict

def identify_and_print_rows(csv_filename):
    """Identify rows based on specific conditions."""
    
    row_occurrences = defaultdict(int)
    rows = []

    # Gather all rows and populate the defaultdict
    with open(csv_filename, 'r') as f:
        reader = csv.reader(f)
        for row in reader:
            row_occurrences[tuple(row)] += 1  # use tuple as keys since lists are unhashable
            rows.append(row)

    matching_rows = []
    duplicates_to_remove = set()

    print("Rows where value before and after the comma are the same:")
    for row in rows:
        if len(row) == 2 and row[0] == row[1]:
            print(','.join(row))
            matching_rows.append(tuple(row))

    print("\nDuplicate rows (identical values in all cells):")
    for key, count in row_occurrences.items():
        if count > 1:
            duplicates_to_remove.add(key)
            print(','.join(key))

    # Ask the user if they want to delete the identified rows
    response = input("\nDo you want to delete these rows from the CSV file? (yes or no): ").strip().lower()
    if response == "yes":
        with open(csv_filename, 'w', newline='') as f:
            writer = csv.writer(f)
            already_written = set()  # To keep track of duplicates already written
            for row in rows:
                # Check if the row is a duplicate and has not been written yet, or if it's not a duplicate
                if (tuple(row) in duplicates_to_remove and tuple(row) not in already_written) or tuple(row) not in duplicates_to_remove:
                    writer.writerow(row)
                    already_written.add(tuple(row))
        print("Duplicate rows deleted successfully.")
    else:
        print("No changes made to the CSV file.")

if __name__ == '__main__':
    csv_filename = 'singlerowstest.csv'
    identify_and_print_rows(csv_filename)
