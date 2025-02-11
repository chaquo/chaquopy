use codspeed_bencher_compat::{benchmark_group, benchmark_main, Bencher};

use std::fs::File;
use std::io::Read;

use pyo3::Python;

use jiter::{cache_clear, PythonParse, StringCacheMode};

fn python_parse_numeric(bench: &mut Bencher) {
    Python::with_gil(|py| {
        cache_clear();
        bench.iter(|| {
            PythonParse::default()
                .python_parse(
                    py,
                    br#"  { "int": 1, "bigint": 123456789012345678901234567890, "float": 1.2}  "#,
                )
                .unwrap()
        });
    })
}

fn python_parse_other(bench: &mut Bencher) {
    Python::with_gil(|py| {
        cache_clear();
        bench.iter(|| {
            PythonParse::default()
                .python_parse(py, br#"["string", true, false, null]"#)
                .unwrap()
        });
    })
}

fn _python_parse_file(path: &str, bench: &mut Bencher, cache_mode: StringCacheMode) {
    let mut file = File::open(path).unwrap();
    let mut contents = String::new();
    file.read_to_string(&mut contents).unwrap();
    let json_data = contents.as_bytes();

    Python::with_gil(|py| {
        cache_clear();
        bench.iter(|| {
            PythonParse {
                cache_mode,
                ..Default::default()
            }
            .python_parse(py, json_data)
            .unwrap()
        });
    })
}

fn python_parse_massive_ints_array(bench: &mut Bencher) {
    _python_parse_file("./benches/massive_ints_array.json", bench, StringCacheMode::All);
}

fn python_parse_medium_response_not_cached(bench: &mut Bencher) {
    _python_parse_file("./benches/medium_response.json", bench, StringCacheMode::None);
}

fn python_parse_medium_response(bench: &mut Bencher) {
    _python_parse_file("./benches/medium_response.json", bench, StringCacheMode::All);
}

fn python_parse_true_object_not_cached(bench: &mut Bencher) {
    _python_parse_file("./benches/true_object.json", bench, StringCacheMode::None);
}

fn python_parse_string_array_not_cached(bench: &mut Bencher) {
    _python_parse_file("./benches/string_array.json", bench, StringCacheMode::None);
}

fn python_parse_string_array(bench: &mut Bencher) {
    _python_parse_file("./benches/string_array.json", bench, StringCacheMode::All);
}

fn python_parse_x100_not_cached(bench: &mut Bencher) {
    _python_parse_file("./benches/x100.json", bench, StringCacheMode::None);
}

fn python_parse_x100(bench: &mut Bencher) {
    _python_parse_file("./benches/x100.json", bench, StringCacheMode::All);
}

fn python_parse_string_array_unique_not_cached(bench: &mut Bencher) {
    _python_parse_file("./benches/string_array_unique.json", bench, StringCacheMode::None);
}

fn python_parse_string_array_unique(bench: &mut Bencher) {
    _python_parse_file("./benches/string_array_unique.json", bench, StringCacheMode::All);
}

fn python_parse_true_object(bench: &mut Bencher) {
    _python_parse_file("./benches/true_object.json", bench, StringCacheMode::All);
}

/// Note - caching strings should make no difference here
fn python_parse_true_array(bench: &mut Bencher) {
    _python_parse_file("./benches/true_array.json", bench, StringCacheMode::All);
}

benchmark_group!(
    benches,
    python_parse_numeric,
    python_parse_other,
    python_parse_medium_response_not_cached,
    python_parse_medium_response,
    python_parse_true_object_not_cached,
    python_parse_string_array_not_cached,
    python_parse_string_array,
    python_parse_string_array_unique_not_cached,
    python_parse_string_array_unique,
    python_parse_x100_not_cached,
    python_parse_x100,
    python_parse_true_object,
    python_parse_true_array,
    python_parse_massive_ints_array,
);
benchmark_main!(benches);
