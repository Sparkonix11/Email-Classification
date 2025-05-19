"""
Script to upload the email classification model to Hugging Face Hub
"""

import sys
import argparse
import subprocess
import pkg_resources


def check_and_install_dependencies():
    """Check for required libraries and install if missing"""
    required_packages = ['torch', 'transformers', 'sentencepiece']
    installed_packages = {pkg.key for pkg in pkg_resources.working_set}

    missing_packages = [pkg for pkg in required_packages if pkg not in installed_packages]

    if missing_packages:
        missing_packages_str = ", ".join(missing_packages)
        print(f"Installing missing dependencies: {missing_packages_str}")
        subprocess.check_call([sys.executable, "-m", "pip", "install"]
                              + missing_packages)
        print("Dependencies installed. You may need to restart the script.")
        return False

    return True


def get_huggingface_username(token=None):
    """Get the username for the authenticated user"""
    try:
        from huggingface_hub import HfApi
        api = HfApi(token=token)
        user_info = api.whoami()
        return user_info.get('name')
    except Exception as e:
        print(f"Error getting Hugging Face username: {e}")
        return None


def main():
    """Upload model to Hugging Face Hub"""
    # Check dependencies first
    if not check_and_install_dependencies():
        return

    # Import dependencies after installation check
    from transformers import XLMRobertaForSequenceClassification, XLMRobertaTokenizer
    from huggingface_hub import login

    parser = argparse.ArgumentParser(
        description="Upload email classification model to Hugging Face Hub")
    parser.add_argument("--model_path", type=str, default="classification_model",
                        help="Local path to the model files")
    parser.add_argument("--hub_model_id", type=str,
                        help="Hugging Face Hub model ID (e.g., "
                             "'username/email-classifier-model')")
    parser.add_argument("--model_name", type=str, default="email-classifier-model",
                        help="Name for the model repository "
                             "(default: email-classifier-model)")
    parser.add_argument("--token", type=str,
                        help="Hugging Face API token (optional, can use "
                             "environment variable or huggingface-cli login)")

    args = parser.parse_args()

    # Login if token is provided
    if args.token:
        login(token=args.token)

    # If hub_model_id is not provided, try to get username and construct it
    if not args.hub_model_id:
        username = get_huggingface_username(args.token)
        if not username:
            print("Could not determine Hugging Face username. "
                  "Please provide --hub_model_id explicitly.")
            return
        args.hub_model_id = f"{username}/{args.model_name}"

    print(f"Loading model from {args.model_path}...")
    # Load the local model and tokenizer
    model = XLMRobertaForSequenceClassification.from_pretrained(args.model_path)
    tokenizer = XLMRobertaTokenizer.from_pretrained(args.model_path)

    print(f"Uploading model to {args.hub_model_id}...")
    try:
        # Push to Hugging Face Hub
        model.push_to_hub(args.hub_model_id)
        tokenizer.push_to_hub(args.hub_model_id)

        print("Model successfully uploaded to Hugging Face Hub!")
        print(f"You can now use the model with the ID: {args.hub_model_id}")
        print(f"Update the MODEL_PATH in Dockerfile to: {args.hub_model_id}")
    except Exception as e:
        print(f"Error uploading model: {e}")
        print("\nPossible solutions:")
        print("1. Make sure you're logged in with 'huggingface-cli login'")
        print("2. Check that you have permission to create repos in the "
              "specified namespace")
        print("3. Try using your own username: "
              "--hub_model_id yourusername/email-classifier-model")


if __name__ == "__main__":
    main()
