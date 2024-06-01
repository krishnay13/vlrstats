def add_prefix_to_match_ids(input_file, output_file, prefix='https://vlr.gg/'):
    try:
        with open(input_file, 'r') as infile, open(output_file, 'w') as outfile:
            for line in infile:
                match_id = line.strip()
                full_url = f"{prefix}{match_id}"
                outfile.write(full_url + '\n')
        print(f"URLs with prefix added successfully. Check {output_file} for the results.")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    input_file = 'matches.txt'
    output_file = 'full_matches.txt'
    add_prefix_to_match_ids(input_file, output_file)
