pre_calculated_date_frequencies = [
    [-400, -351, 12.807954545454544],
    [-350, -301, 80.18097041847041],
    [-300, -251, 1703.6647366522352],
    [-250, -201, 2433.331403318906],
    [-200, -151, 1409.831403318903],
    [-150, -101, 1939.7480699855676],
    [-100, -51, 816.0814033189039],
    [-50, -1, 875.6528318903318],
    [1, 50, 2123.265927128423],
    [51, 100, 3496.2659271284374],
    [101, 150, 8169.871482683945],
    [151, 200, 6992.763149350619],
    [201, 250, 5228.363149350657],
    [251, 300, 4414.779816017322],
    [301, 350, 3725.4500541125603],
    [351, 400, 2232.7833874458793],
    [401, 450, 1149.8946969696945],
    [451, 500, 923.5946969696963],
    [501, 550, 1878.8946969696985],
    [551, 600, 2040.3030303030314],
    [601, 650, 2870.719696969714],
    [651, 700, 1430.3863636363678],
    [701, 750, 1584.0825757575653],
    [751, 800, 686.4492424242436],
    [801, 850, 14.083333333333334],
    [851, 900, 7.749999999999999],
    [901, 950, 4.416666666666667],
    [951, 1000, 2.0833333333333335],
    [1001, 1050, 1.5833333333333333],
    [1051, 1100, 0.5833333333333333],
    [1101, 1150, 0.16666666666666666],
    [1151, 1200, 0.16666666666666666],
]

pre_calculated_token_frequencies = [
    [-400, -351, 302.68295454545455],
    [-350, -301, 5795.7147005772],
    [-300, -251, 148491.96037157282],
    [-250, -201, 228872.6270382396],
    [-200, -151, 156741.21037157284],
    [-150, -101, 239526.96037157287],
    [-100, -51, 73458.21037157286],
    [-50, -1, 81191.11513347761],
    [1, 50, 201938.12703823944],
    [51, 100, 242640.293704906],
    [101, 150, 594466.5381493518],
    [151, 200, 694867.3381493507],
    [201, 250, 463868.55481601716],
    [251, 300, 328957.13814935077],
    [301, 350, 324750.27505411266],
    [351, 400, 149151.35838744583],
    [401, 450, 64196.67445887446],
    [451, 500, 80435.9411255411],
    [501, 550, 214354.00779220776],
    [551, 600, 266408.3577922077],
    [601, 650, 171898.35779220788],
    [651, 700, 90939.69112554108],
    [701, 750, 194973.5492424243],
    [751, 800, 59965.982575757575],
    [801, 850, 1449.1666666666665],
    [851, 900, 564.3333333333333],
    [901, 950, 149.5],
    [951, 1000, 56.166666666666664],
    [1001, 1050, 179.91666666666666],
    [1051, 1100, 32.916666666666664],
    [1101, 1150, 11.166666666666666],
    [1151, 1200, 11.166666666666666],
]

pre_calculated_date_range_average = 62


def get_document_date_ranges():
    dates_bce = [range(x, x + 50) for x in range(-400, 0, 50)]
    dates_ce = [range(x, x + 50) for x in range(1, 1201, 50)]
    return dates_bce + dates_ce


def get_text_date_frequencies(texts):
    dates = get_document_date_ranges()
    date_limits = [(list(x)[0], list(x)[-1]) for x in dates]
    frequency_index = [0.0] * len(dates)
    n_full_ranges = 0
    ranges = 0
    average_range = pre_calculated_date_range_average

    # Iterate all texts
    for d in texts:
        dnb = d["date_not_before"]
        dna = d["date_not_after"]
        token_count = d.get("token_count", 1)
        # Require some date
        if not (dnb or dna):
            continue

        # If both dates are set, add to counter
        full_range = True if (dnb and dna) else False

        # If only other date, use average range
        if not (dnb and dna):
            if not dnb:
                dnb = dna - average_range
            if not dna:
                dna = dnb + average_range

        # Reverse if dates in wrong order
        if dnb > dna:
            temp = dnb
            dnb = dna
            dna = temp

        # Init matching date list with zeros
        matching_date_ranges = [0] * len(dates)

        this_range = range(dnb, dna + 1)

        # If full range, collect to calculate average range
        if full_range:
            ranges += len(this_range)
            n_full_ranges += 1

        # Iterate dates
        for i, date_range in enumerate(dates):
            if set(this_range).intersection(date_range):
                matching_date_ranges[i] = 1

        # Count matching date ranges
        n_matches = sum(matching_date_ranges)

        if not n_matches:
            continue

        result = [(x / n_matches) * token_count for x in matching_date_ranges]
        frequency_index = [sum(i) for i in zip(result, frequency_index)]

    # print("average range")
    # print(ranges / n_full_ranges)

    def round_to_zero(y):
        if y < 0.5:
            return 0.00001
        return y

    res = [
        [x[0], x[1], round_to_zero(y), round_to_zero(y) / z[-1]]
        for x, y, z in zip(
            date_limits, frequency_index, pre_calculated_token_frequencies
        )
    ]
    return res
