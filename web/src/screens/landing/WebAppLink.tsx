import type { ReactNode } from "react";
import { Link } from "react-router-dom";
import { isExternalWebApp, webAppURL } from "../../core/webApp";

/** Landing CTA into the product app. External when Pages ≠ origin. */
export function WebAppLink({
  className,
  children,
  path = "/app",
  ...rest
}: {
  className?: string;
  children: ReactNode;
  path?: string;
  "data-od-id"?: string;
}) {
  if (isExternalWebApp()) {
    return (
      <a className={className} href={webAppURL(path)} {...rest}>
        {children}
      </a>
    );
  }
  return (
    <Link className={className} to={path} {...rest}>
      {children}
    </Link>
  );
}
