func positiveCount(_ values: [Int]) -> Int {
    let selected = values.filter { $0 > 0 }
    return selected.count
}

func largeCount(_ items: [Int]) -> Int {
    let kept = items.filter { $0 > 100 }
    return kept.count
}
