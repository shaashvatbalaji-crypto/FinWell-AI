from mysql_pipeline.document_storage import (
    get_document_by_id,
    list_user_documents,
    update_document_status,
)


def run_test():
    # The earlier test created user_id=1 and document_id=1.
    user_id = 1
    document_id = 1

    print("\n1. Test retrieving a document")
    result = get_document_by_id(document_id, user_id)
    print(result)

    if result["success"]:
        print("PASS: Document retrieved.")
    else:
        print("FAIL: Could not retrieve document.")

    print("\n2. Test listing user documents")
    result = list_user_documents(user_id)
    print(result)

    if result["success"]:
        print("PASS: User documents listed.")
    else:
        print("FAIL: Could not list documents.")

    print("\n3. Test updating document status")
    result = update_document_status(
        document_id=document_id,
        user_id=user_id,
        status="processing",
    )
    print(result)

    if result["success"]:
        print("PASS: Document status updated.")
    else:
        print("FAIL: Could not update status.")


if __name__ == "__main__":
    run_test()