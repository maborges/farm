"use client"

import { useState, useMemo } from "react"

export type SortConfig = {
  key: string
  direction: "asc" | "desc"
} | null

export type UseDataTableProps<T> = {
  data: T[]
  initialSort?: SortConfig
}

export function useDataTable<T extends Record<string, any>>({
  data,
  initialSort = null,
}: UseDataTableProps<T>) {
  const [sortConfig, setSortConfig] = useState<SortConfig>(initialSort)
  const [filters, setFilters] = useState<Record<string, string>>({})
  const [globalFilter, setGlobalFilter] = useState("")

  const sortedData = useMemo(() => {
    if (!sortConfig) return data

    return [...data].sort((a, b) => {
      const aValue = a[sortConfig.key]
      const bValue = b[sortConfig.key]

      if (aValue === null || aValue === undefined) return 1
      if (bValue === null || bValue === undefined) return -1

      if (aValue < bValue) {
        return sortConfig.direction === "asc" ? -1 : 1
      }
      if (aValue > bValue) {
        return sortConfig.direction === "asc" ? 1 : -1
      }
      return 0
    })
  }, [data, sortConfig])

  const filteredData = useMemo(() => {
    return sortedData.filter((row) => {
      // Column filters
      const columnFiltersMatch = Object.entries(filters).every(
        ([key, value]) => {
          if (!value) return true
          const cellValue = row[key]?.toString().toLowerCase() || ""
          return cellValue.includes(value.toLowerCase())
        }
      )

      if (!columnFiltersMatch) return false

      // Global filter
      if (globalFilter) {
        return Object.values(row).some((value) => {
          const stringValue = value?.toString().toLowerCase() || ""
          return stringValue.includes(globalFilter.toLowerCase())
        })
      }

      return true
    })
  }, [sortedData, filters, globalFilter])

  const handleSort = (key: string) => {
    setSortConfig((current) => {
      if (!current || current.key !== key) {
        return { key, direction: "asc" }
      }
      if (current.direction === "asc") {
        return { key, direction: "desc" }
      }
      return null
    })
  }

  const handleFilter = (key: string, value: string) => {
    setFilters((prev) => ({
      ...prev,
      [key]: value,
    }))
  }

  const clearFilter = (key: string) => {
    setFilters((prev) => {
      const newFilters = { ...prev }
      delete newFilters[key]
      return newFilters
    })
  }

  const clearAllFilters = () => {
    setFilters({})
    setGlobalFilter("")
  }

  return {
    data: filteredData,
    sortConfig,
    filters,
    globalFilter,
    handleSort,
    handleFilter,
    clearFilter,
    clearAllFilters,
    setGlobalFilter,
    totalRecords: data.length,
    filteredRecords: filteredData.length,
  }
}
