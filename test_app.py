"""Smoke test for the Streamlit app: runs the script headless and checks for exceptions.
Run: python test_app.py"""
import time
from streamlit.testing.v1 import AppTest

t = time.time()
at = AppTest.from_file("app.py", default_timeout=300)
at.run()
print(f"first run {time.time() - t:.1f} s; exceptions: {len(at.exception)}")
for e in at.exception:
    print(e.message)
    print("\n".join(e.stack_trace[-12:]))
print("metrics:", [(m.label, m.value, m.delta) for m in at.metric])
print("dataframes:", len(at.dataframe))
if at.dataframe:
    print(at.dataframe[0].value.to_string())

# change look-ahead to a year and add the Apollo 11 site
at.sidebar.selectbox[0].set_value("1 year").run()
print("1-year run exceptions:", len(at.exception))
at.sidebar.multiselect[0].set_value(["Apollo 11 (Mare Tranquillitatis), 1969",
                                     "Chang'e 4 (Von Kármán crater), landed 2019"]).run()
print("Apollo/Chang'e run exceptions:", len(at.exception))
for e in at.exception:
    print(e.message)
    print("\n".join(e.stack_trace[-12:]))
print("metrics:", [(m.label, m.value, m.delta) for m in at.metric])
# move-the-site grid
at.button[0].click().run() if at.button else None
print("after button exceptions:", len(at.exception))
for e in at.exception:
    print(e.message)
    print("\n".join(e.stack_trace[-12:]))
print(f"total {time.time() - t:.1f} s")
