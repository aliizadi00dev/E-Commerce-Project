from enum import StrEnum


class StoreStatus(StrEnum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class ProductStatus(StrEnum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    OUT_OF_STOCK = "out_of_stock"


class CartStatus(StrEnum):
    ACTIVE = "active"
    CHECKED_OUT = "checked_out"
    CANCELLED = "cancelled"


class OrderStatus(StrEnum):
    PENDING = "pending"
    PAID = "paid"
    CANCELLED = "cancelled"
    SHIPPED = "shipped"
    DELIVERED = "delivered"


class StoreOrderStatus(StrEnum):
    PENDING = "pending"
    PAID = "paid"
    CANCELLED = "cancelled"
    SHIPPED = "shipped"
    DELIVERED = "delivered"


class PaymentStatus(StrEnum):
    PENDING = "pending"
    PAID = "paid"
    FAILED = "failed"
    REFUNDED = "refunded"


class PaymentMethod(StrEnum):
    WALLET = "wallet"
    GATEWAY = "gateway"
    CARD = "card"


class WalletTransactionType(StrEnum):
    CREDIT = "credit"
    DEBIT = "debit"


class WalletTransactionStatus(StrEnum):
    COMPLETED = "completed"
    PENDING = "pending"
    FAILED = "failed"


def sql_values(enum_type: type[StrEnum]) -> str:
    return ", ".join(f"'{member.value}'" for member in enum_type)
