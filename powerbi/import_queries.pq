// Power Query M — import queries for the lab billing research model
// Apply one query per table (Power Query > Advanced Editor).

let
    // ---- Lineages ----
    Lineages = let
        Source = Csv.Document(File.Contents("outputs/runs/<run>/module_a/lineages.csv"),
                              [Delimiter=",", Columns=18, Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
        Promoted = Table.PromoteHeaders(Source, [PromoteAllHeaders=true])
    in Promoted,

    // ---- Lineage membership bridge ----
    // record_ids is a pipe-delimited list; expand it into rows.
    LineageMember = let
        Source = Lineages,
        Split = Table.TransformColumns(Source, {{"record_ids",
                 each Text.Split(_, "|"), type list}}),
        Expanded = Table.ExpandListColumn(Split, "record_ids")
    in Expanded,

    // ---- Bills ----
    Bills = let
        Source = Csv.Document(File.Contents("outputs/runs/<run>/data/bills.csv"),
                              [Delimiter=",", Columns=13, Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
        Promoted = Table.PromoteHeaders(Source, [PromoteAllHeaders=true])
    in Promoted,

    // ---- Events ----
    Events = let
        Source = Csv.Document(File.Contents("outputs/runs/<run>/module_a/events_normalized.csv"),
                              [Delimiter=",", Columns=13, Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
        Promoted = Table.PromoteHeaders(Source, [PromoteAllHeaders=true])
    in Promoted,

    // ---- Allocations ----
    Allocations = let
        Source = Csv.Document(File.Contents("outputs/runs/<run>/module_a/allocations_normalized.csv"),
                              [Delimiter=",", Columns=7, Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
        Promoted = Table.PromoteHeaders(Source, [PromoteAllHeaders=true])
    in Promoted,

    // ---- Predictions ----
    Predictions = let
        Source = Csv.Document(File.Contents("outputs/runs/<run>/module_b/predictions.csv"),
                              [Delimiter=",", Columns=10, Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
        Promoted = Table.PromoteHeaders(Source, [PromoteAllHeaders=true])
    in Promoted
in
    Lineages
