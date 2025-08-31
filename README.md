# Coursplit

This software takes a course registration Excel file as an input, and by analyzing students' course selections, it computes their availability for different time slots. Using this information, it suggests all available time slots where a new or alternative section of a specified course can be scheduled, ensuring that a minimum number of students can attend. The software will also automatically generate a list of student to keep and shift between sections.

## Usage

To run this application locally, open your terminal/command prompt and execute this command:

```bash
git clone https://github.com/SepehrAkbari/coursplit.git
cd coursplit

python -m venv .venv
source .venv/bin/activate # On Windows use `.venv\Scripts\activate`

pip install -r requirements.txt

streamlit run app.py
```

## Contributing

Feel free to fork the repository, open issues, or submit pull requests for enhancements. If you find a bug or want to suggest a new feature, start a discussion!

## License

This project is licensed under the [GNU General Public License (GPL)](/LICENSE).
