def yoe_score(yoe):
    if 5 <= yoe <= 9:    return 15
    elif 4 <= yoe < 5:   return 12
    elif 9 < yoe <= 12:  return 10
    elif 3 <= yoe < 4:   return 6
    elif 12 < yoe <= 15: return 5
    elif yoe > 15:       return 2
    else:                return 0
