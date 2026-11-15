fun positiveCount(values: List<Int>): Int {
    val selected = values.filter { it > 0 }
    return selected.count()
}

fun largeCount(items: List<Int>): Int {
    val kept = items.filter { it > 100 }
    return kept.count()
}
