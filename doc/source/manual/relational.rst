column_property example:

```
Invoice.append_field('cost', Decimal(
    exc_db=True,
    str_format="${:,.2f}",
    read_only=True,
    mapper_property=column_property(sql
        .select([sql.func.sum(InvoiceItem.cost)])
        .where(
            D91InvoiceItem.invoice_id == Invoice.id,
        )
        .as_scalar()
    ),
))
```
